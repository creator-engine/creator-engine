#!/usr/bin/env python3
"""Host-side contained-seat SELF-PUSH broker daemon CLI."""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from collections.abc import Callable

# Make the sibling ``egress_broker`` package importable when run as a script, and put the
# repo's ``validators/`` on the path so reused forge primitives import without env setup.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
_VALIDATORS = os.path.join(_REPO_ROOT, "validators")
if os.path.isdir(_VALIDATORS):
    sys.path.insert(0, _VALIDATORS)

from egress_broker.config import BrokerConfigError, load_broker_config  # noqa: E402
from egress_broker.host_broker import serve_self_push_unix_socket  # noqa: E402
from egress_broker.minter import (  # noqa: E402
    EgressSignerError,
    VaultKvConfig,
    make_signer_for_seat,
)

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 2
EXIT_CONFIG_ERROR = 3

_APPROLE_LOGIN_TIMEOUT_S = 10.0


class _BrokerStartupError(Exception):
    """Fail-closed startup error; message is safe to print (no secrets)."""


def _approle_token_supplier(
    role_id: str,
    secret_id: str,
    bao_addr: str,
    ca_bundle: str | None,
) -> Callable[[], str]:
    """Return a callable that performs a fresh AppRole login and returns the client_token.

    Each call POSTs to ``{bao_addr}/v1/auth/approle/login`` with the role_id/secret_id,
    verifies TLS via ``ssl.create_default_context(cafile=ca_bundle)``, parses the
    ``auth.client_token`` field, and returns it.  Fail-closed: any HTTP error, transport
    error, JSON parse error, or an empty/missing token raises :class:`EgressSignerError`
    WITHOUT including the secret_id or token in the message.  Timeout is
    ``_APPROLE_LOGIN_TIMEOUT_S`` seconds.
    """
    url = f"{bao_addr.rstrip('/')}/v1/auth/approle/login"

    def _login() -> str:
        body = json.dumps({"role_id": role_id, "secret_id": secret_id}).encode("utf-8")
        ssl_context: ssl.SSLContext | None = None
        if url.startswith("https://"):
            ssl_context = ssl.create_default_context(cafile=ca_bundle)
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        raw: bytes
        try:
            with urllib.request.urlopen(
                request, timeout=_APPROLE_LOGIN_TIMEOUT_S, context=ssl_context
            ) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            raise EgressSignerError(
                f"AppRole login to {bao_addr} failed with HTTP {exc.code}; "
                "refusing to start (credentials redacted)"
            ) from None
        except (urllib.error.URLError, OSError):
            raise EgressSignerError(
                f"AppRole login to {bao_addr} failed (transport error); "
                "refusing to start (credentials redacted)"
            ) from None

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise EgressSignerError(
                f"AppRole login response from {bao_addr} is not valid JSON; "
                "refusing to start"
            ) from None

        auth = payload.get("auth") if isinstance(payload, dict) else None
        token = auth.get("client_token") if isinstance(auth, dict) else None
        if not token or not isinstance(token, str):
            raise EgressSignerError(
                f"AppRole login to {bao_addr} did not return a client_token; "
                "refusing to start (response value redacted)"
            )
        return token

    return _login


def _build_signer(seat, *, env: dict[str, str] | None = None):
    """Build the appropriate signer for a seat, routing by secret_ref vs pem_path.

    Vault-backed seats (secret_ref present):
      - Reads BAO_ADDR (fallback VAULT_ADDR), BAO_CACERT (fallback VAULT_CACERT),
        BROKER_APPROLE_ROLE_ID, BROKER_APPROLE_SECRET_ID from environment.
      - Any missing variable is a fail-closed :class:`_BrokerStartupError` — NEVER silently
        falls back to pem_path/disk.
      - Logs only ``seat_id + "vault-backed"`` — never role_id, secret_id, or token.

    PEM-backed seats (pem_path, no secret_ref):
      - Delegates to :func:`make_signer_for_seat` which calls ``openssl_signer``.
      - Logs ``seat_id + "pem-backed"``.

    Raises :class:`_BrokerStartupError` on misconfiguration (safe message, no secrets).
    Raises :class:`EgressSignerError` on vault/openssl failures downstream.
    """
    e = env if env is not None else dict(os.environ)

    if seat.secret_ref is not None:
        # --- Vault-backed path (ce-ops#267) ---
        bao_addr = e.get("BAO_ADDR") or e.get("VAULT_ADDR") or ""
        bao_cacert = e.get("BAO_CACERT") or e.get("VAULT_CACERT") or None
        role_id = e.get("BROKER_APPROLE_ROLE_ID") or ""
        secret_id = e.get("BROKER_APPROLE_SECRET_ID") or ""

        missing: list[str] = []
        if not bao_addr:
            missing.append("BAO_ADDR (or VAULT_ADDR)")
        if not role_id:
            missing.append("BROKER_APPROLE_ROLE_ID")
        if not secret_id:
            missing.append("BROKER_APPROLE_SECRET_ID")
        if missing:
            raise _BrokerStartupError(
                f"seat {seat.seat_id!r} has a secret_ref but the following required vault env "
                f"vars are missing or empty: {', '.join(missing)}. "
                "Refusing to start — NEVER falling back to disk."
            )

        token_supplier = _approle_token_supplier(role_id, secret_id, bao_addr, bao_cacert)
        vault_cfg = VaultKvConfig(
            address=bao_addr,
            token_supplier=token_supplier,
            ca_bundle=bao_cacert,
            verify_tls=True,
        )
        print(
            f"[ce-egress-self-push] seat {seat.seat_id!r}: vault-backed signer initialised",
            file=sys.stderr,
        )
        return make_signer_for_seat(seat, vault_config=vault_cfg)

    # --- PEM-backed path (legacy) ---
    print(
        f"[ce-egress-self-push] seat {seat.seat_id!r}: pem-backed signer initialised",
        file=sys.stderr,
    )
    return make_signer_for_seat(seat, vault_config=None)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ce-egress-self-push-broker",
        description="Host-side Unix-socket daemon for contained-seat SELF-PUSH requests.",
    )
    parser.add_argument("--socket", required=True, help="host Unix socket path for this seat")
    parser.add_argument("--seat", required=True, help="broker seat id bound to this socket, e.g. dev-4")
    parser.add_argument(
        "--host-repo-path",
        required=True,
        help="trusted host repo path; any request repo_path is ignored",
    )
    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/.ce-egress/broker.json"),
        help="host broker config JSON",
    )
    parser.add_argument("--once", action="store_true", help="serve one request then exit")
    return parser


def main(argv=None, *, serve_fn=None, signer_factory=None) -> int:
    """Parse args, build host-owned seams, and run the Unix-socket broker."""
    args = _build_parser().parse_args(argv)
    run_server = serve_fn or serve_self_push_unix_socket

    try:
        config = load_broker_config(args.config)
        seat = config.seat(args.seat)
    except BrokerConfigError as exc:
        print(f"[ce-egress-self-push] config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    try:
        # When a signer_factory is injected (tests), use it directly on pem_path for
        # back-compat with the existing test_egress_cli.py test surface.  In production
        # (signer_factory=None), route through _build_signer which selects vault vs pem.
        if signer_factory is not None:
            signer = signer_factory(seat.pem_path)
        else:
            signer = _build_signer(seat)
        run_server(
            args.socket,
            config=config,
            broker_seat_id=args.seat,
            host_repo_path=args.host_repo_path,
            signer=signer,
            once=args.once,
        )
    except _BrokerStartupError as exc:
        print(f"[ce-egress-self-push] startup error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except Exception as exc:  # noqa: BLE001 - process boundary maps all runtime failures to code 2.
        # EgressRefused is serialized by host_broker into JSON; it does not escape here.
        # Deliberately do not print ``str(exc)``; subprocess/socket errors can contain
        # credential-shaped stderr from lower transports.
        print(
            f"[ce-egress-self-push] broker runtime error: {type(exc).__name__}",
            file=sys.stderr,
        )
        return EXIT_RUNTIME_ERROR
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
