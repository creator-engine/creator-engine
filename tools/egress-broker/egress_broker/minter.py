"""The generalized per-App egress minter — installation-id discovery + least-privilege mint.

The brief's minter pattern (the existing ``mint-forge-token`` flow) is: build an RS256 App JWT
``{iat:now-60, exp:now+540, iss:app_id}``, ``POST /app/installations/{id}/access_tokens`` to
get a (~1h) installation token. This module GENERALIZES it across the per-dev Apps and adds the
missing leg — installation-id discovery when the config doesn't record one (dev-4):

1. resolve the installation id: use ``seat.installation_id`` if set, else
   :func:`~egress_broker.installation.discover_installation_id` (``GET /app/installations``
   filtered to the org);
2. mint a JIT, least-privilege, time-boxed installation token through the FROZEN seams —
   ``forge.app_jwt_runner.app_jwt_gh_runner`` (App-JWT Bearer mint adapter) feeding
   ``forge.scoped_token.mint_scoped_token`` (the ceiling-validated minter). The permission
   ceiling, redaction, and refuse-before-side-effect are all the existing, tested ones — this
   module only composes them per-App with discovery.

Secret hygiene (inherited from the frozen seams): the App PRIVATE KEY stays behind the
:func:`openssl_signer` ``openssl dgst -sha256 -sign`` subprocess (the PEM is only a path; the
key never enters this process); the JWT is header-only; the minted token value lives only in
the returned :class:`ScopedToken` (redacted from its repr). One injectable ``transport`` drives
both discovery and mint; tests use a fake and run ZERO live crypto/network.

Vault-backed signing (ce-ops#266): when a seat specifies ``secret_ref`` instead of
``pem_path``, :func:`vault_signer` fetches the App private key from OpenBao per-call (KV v2
GET at ``<mount>/data/<path>``), pipes it to ``openssl`` via ``/dev/fd/<N>`` (key never written
to disk), then zeroises the in-memory copy.  The :class:`VaultKvConfig` carries injectable
address/CA/token seams so tests use a mock vault client with zero live I/O.  Fail-closed: any
vault read error raises :class:`EgressSignerError` before signing — never falls back to disk.
"""
from __future__ import annotations

import ctypes
import json
import os
import ssl
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from creator_engine_validator.forge.app_jwt_runner import Signer, app_jwt_gh_runner
from creator_engine_validator.forge.scoped_token import ScopedToken, TokenRequest, mint_scoped_token
from egress_broker.config import SeatAppConfig, VaultSecretRef
from egress_broker.installation import Transport, discover_installation_id


class EgressSignerError(Exception):
    """The App private key could not produce an RS256 signature — fail-closed, refuse to mint."""


def openssl_signer(pem_path: str, *, runner: Callable[..., Any] = subprocess.run) -> Signer:
    """Return an RS256 :data:`~forge.app_jwt_runner.Signer` backed by ``openssl dgst -sha256 -sign``.

    Mirrors ``v3_forge_join.openssl_signer`` (re-defined locally so the broker is self-contained
    and pulls in none of the heavy v3 join graph): the signing input goes to openssl on STDIN and
    openssl reads the PEM itself, so the **App private key NEVER enters the broker process**. A
    non-zero exit or an empty signature is a fail-closed :class:`EgressSignerError`. ``runner`` is
    the injectable subprocess seam (CI fakes it → zero live openssl).
    """
    pem = str(pem_path)

    def sign(signing_input: bytes) -> bytes:
        proc = runner(
            ["openssl", "dgst", "-sha256", "-sign", pem], input=signing_input, capture_output=True
        )
        if getattr(proc, "returncode", 1) != 0:
            raise EgressSignerError(
                "openssl RS256 signing failed (the App private key is unreadable or invalid); "
                "refusing to mint"
            )
        signature = getattr(proc, "stdout", b"") or b""
        if not signature:
            raise EgressSignerError("openssl produced an empty RS256 signature; refusing to mint")
        return signature

    return sign


# ---------------------------------------------------------------------------
# Vault-backed signer (ce-ops#266)
# ---------------------------------------------------------------------------

VaultFetcher = Callable[[VaultSecretRef], str]
"""Injectable callable: given a VaultSecretRef, return the raw PEM string — fail-closed."""


@dataclass(frozen=True)
class VaultKvConfig:
    """Injectable OpenBao/Vault KV v2 client config for the vault-backed signer.

    ``address`` is ``BAO_ADDR``/``VAULT_ADDR``; ``token_supplier`` returns the broker's
    read-only AppRole token at call time (never embedded here); ``ca_bundle`` is a host-local
    CA bundle path for TLS verification (None → system CAs); ``verify_tls`` controls
    certificate verification (must be True in production).  All I/O is injectable for tests.
    """

    address: str
    token_supplier: Callable[[], str] = field(repr=False)
    ca_bundle: str | None = None
    verify_tls: bool = True

    def __repr__(self) -> str:
        return (
            f"VaultKvConfig(address={self.address!r}, ca_bundle={self.ca_bundle!r}, "
            f"verify_tls={self.verify_tls!r}, token_supplier=<injected>)"
        )

    __str__ = __repr__


def _zeroise(buf: bytearray) -> None:
    """Best-effort in-memory zeroisation of a secret bytearray."""
    try:
        ctypes.memset(ctypes.addressof(ctypes.c_char.from_buffer(buf)), 0, len(buf))
    except Exception:  # noqa: BLE001 — zeroisation is best-effort; do not shadow the real error
        for i in range(len(buf)):
            buf[i] = 0


def _default_vault_http_fetch(
    config: VaultKvConfig,
    ref: VaultSecretRef,
) -> str:  # pragma: no cover — live path; covered by unit tests with a mock
    """Live OpenBao KV v2 GET — used only in production (tests inject a mock)."""
    token = config.token_supplier()
    if not token:
        raise EgressSignerError(
            "vault token supplier returned an empty token; refusing to fetch App private key"
        )
    url = f"{config.address.rstrip('/')}/v1/{ref.mount}/data/{ref.path}"
    headers = {
        "Accept": "application/json",
        "X-Vault-Token": token,
    }
    ssl_context: ssl.SSLContext | None = None
    if url.startswith("https://"):
        if config.verify_tls:
            ssl_context = ssl.create_default_context(cafile=config.ca_bundle)
        else:
            ssl_context = ssl._create_unverified_context()  # noqa: S323 — local dev opt-in

    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10.0, context=ssl_context) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raise EgressSignerError(
            f"OpenBao KV read for {ref.mount}/{ref.path} failed with HTTP {exc.code}; "
            "refusing to mint"
        ) from None
    except (urllib.error.URLError, OSError):
        raise EgressSignerError(
            f"OpenBao KV read for {ref.mount}/{ref.path} failed (transport error); "
            "refusing to mint"
        ) from None

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise EgressSignerError(
            f"OpenBao KV response for {ref.mount}/{ref.path} is not valid JSON; refusing to mint"
        ) from None

    return _extract_pem_field(payload, ref)


def _extract_pem_field(payload: Any, ref: VaultSecretRef) -> str:
    """Extract the App private-key field from an OpenBao KV v2 response payload."""
    if not isinstance(payload, Mapping):
        raise EgressSignerError(
            f"OpenBao KV response for {ref.mount}/{ref.path} is not a JSON object; refusing to mint"
        )
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise EgressSignerError(
            f"OpenBao KV response for {ref.mount}/{ref.path} missing 'data' key; refusing to mint"
        )
    fields = data.get("data")
    if not isinstance(fields, Mapping):
        raise EgressSignerError(
            f"OpenBao KV response for {ref.mount}/{ref.path} missing 'data.data' key; "
            "refusing to mint"
        )
    if ref.field not in fields:
        raise EgressSignerError(
            f"OpenBao KV response for {ref.mount}/{ref.path} missing field {ref.field!r}; "
            "refusing to mint"
        )
    value = fields[ref.field]
    if not isinstance(value, str) or not value.strip():
        raise EgressSignerError(
            f"OpenBao KV field {ref.field!r} for {ref.mount}/{ref.path} must be a non-empty "
            "string (PEM); refusing to mint"
        )
    return value


def vault_signer(
    ref: VaultSecretRef,
    config: VaultKvConfig,
    *,
    fetcher: VaultFetcher | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> Signer:
    """Return an RS256 :data:`~forge.app_jwt_runner.Signer` backed by OpenBao App-key custody.

    Per-call flow (ce-ops#266):

    1. Fetch the App private key as a PEM string from OpenBao KV v2 via ``fetcher``
       (default: :func:`_default_vault_http_fetch`; tests inject a mock — ZERO live I/O).
    2. Write the PEM bytes to a ``/dev/fd/<N>`` pipe so ``openssl`` can read it without the
       key ever touching persistent disk.  If anonymous pipe FDs are unavailable (rare), raises
       :class:`EgressSignerError` immediately — never falls back to writing to disk.
    3. Call ``openssl dgst -sha256 -sign /dev/fd/<N>`` with the signing input on STDIN.
    4. Zeroise the in-memory PEM bytearray and close the pipe FD.
    5. Return the raw signature bytes; raise :class:`EgressSignerError` on any failure.

    The App private key NEVER appears in logs, exception messages, or return values. Any vault
    read error, empty token, or openssl failure is a fail-closed :class:`EgressSignerError` —
    no fallback to disk.
    """
    _fetcher: VaultFetcher = fetcher or (lambda r: _default_vault_http_fetch(config, r))

    def sign(signing_input: bytes) -> bytes:
        # --- 1. Fetch key from vault (per-call) ---
        try:
            pem_str = _fetcher(ref)
        except EgressSignerError:
            raise
        except Exception:
            raise EgressSignerError(
                "vault key fetch raised an unexpected error; refusing to mint"
            ) from None

        pem_bytes = bytearray(pem_str.encode("utf-8"))
        # Aggressively remove the str reference; the bytearray is what we zeroize.
        del pem_str

        # --- 2. Feed PEM to openssl via an anonymous pipe (RAM-only, no disk) ---
        try:
            read_fd, write_fd = os.pipe()
        except OSError:
            _zeroise(pem_bytes)
            raise EgressSignerError(
                "could not create an anonymous pipe for vault-backed signing; refusing to mint"
            ) from None

        signature: bytes = b""
        try:
            # Write PEM bytes to the write end; openssl reads from /dev/fd/<read_fd>.
            try:
                os.write(write_fd, pem_bytes)
            finally:
                os.close(write_fd)
                write_fd = -1  # mark closed

            key_fd_path = f"/dev/fd/{read_fd}"
            proc = runner(
                ["openssl", "dgst", "-sha256", "-sign", key_fd_path],
                input=signing_input,
                capture_output=True,
                pass_fds=(read_fd,),
            )

            if getattr(proc, "returncode", 1) != 0:
                raise EgressSignerError(
                    "openssl RS256 signing via vault-fetched key failed; refusing to mint"
                )
            signature = getattr(proc, "stdout", b"") or b""
            if not signature:
                raise EgressSignerError(
                    "openssl produced an empty RS256 signature with vault-fetched key; refusing to mint"
                )
        finally:
            _zeroise(pem_bytes)
            if write_fd != -1:  # close write end if write raised before close
                try:
                    os.close(write_fd)
                except OSError:
                    pass
            try:
                os.close(read_fd)
            except OSError:
                pass

        return signature

    return sign


def make_signer_for_seat(
    seat: SeatAppConfig,
    *,
    vault_config: VaultKvConfig | None = None,
    vault_fetcher: VaultFetcher | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> Signer:
    """Return the appropriate RS256 signer for a seat's configured key source.

    - ``secret_ref`` present → :func:`vault_signer` (vault-backed, per-call fetch, RAM-only).
    - ``pem_path`` present → :func:`openssl_signer` (legacy disk-based; key stays with openssl).

    Raises :class:`EgressSignerError` if neither is configured or if ``secret_ref`` is
    requested but ``vault_config`` is not provided.
    """
    if seat.secret_ref is not None:
        if vault_config is None:
            raise EgressSignerError(
                f"seat {seat.seat_id!r} uses secret_ref but no VaultKvConfig was provided; "
                "refusing to mint"
            )
        return vault_signer(
            seat.secret_ref, vault_config, fetcher=vault_fetcher, runner=runner
        )
    if seat.pem_path is not None:
        return openssl_signer(seat.pem_path, runner=runner)
    raise EgressSignerError(
        f"seat {seat.seat_id!r} has neither secret_ref nor pem_path configured; refusing to mint"
    )


def resolve_installation_id(
    seat: SeatAppConfig,
    *,
    installation_owner: str,
    signer: Signer,
    transport: Transport | None = None,
    now: Callable[[], float] | None = None,
) -> int:
    """Return the seat's App installation id — the recorded one, else discover it (fail-closed)."""
    if seat.installation_id is not None:
        return seat.installation_id
    return discover_installation_id(
        seat.app_id, signer=signer, owner=installation_owner, transport=transport, now=now
    )


def mint_egress_token(
    seat: SeatAppConfig,
    *,
    repo: str,
    installation_owner: str,
    signer: Signer,
    run_id: str,
    policy_sha: str,
    permissions: Mapping[str, str],
    escalation_authority: tuple[tuple[str, str], ...],
    ttl_seconds: int,
    secret_name: str,
    transport: Transport | None = None,
    now: Callable[[], float] | None = None,
) -> ScopedToken:
    """Mint a JIT, least-privilege installation token for ``seat``'s App (discovering id if absent).

    Resolves the installation id (recorded or discovered), then mints through the frozen
    ``app_jwt_gh_runner`` → ``mint_scoped_token`` composition. The request is validated against
    the existing least-privilege ceiling (an out-of-ceiling permission raises ``TokenMintRefused``
    before any forge call). Returns a :class:`ScopedToken` whose value is redacted from its repr.
    """
    installation_id = resolve_installation_id(
        seat, installation_owner=installation_owner, signer=signer, transport=transport, now=now
    )
    app_runner = app_jwt_gh_runner(seat.app_id, signer=signer, transport=transport, now=now)
    request = TokenRequest(
        repo=repo,
        installation_id=installation_id,
        run_id=run_id,
        policy_sha=policy_sha,
        permissions=dict(permissions),
        secret_name=secret_name,
        requested_ttl_seconds=ttl_seconds,
        escalation_authority=escalation_authority,
    )
    return mint_scoped_token(request, gh_runner=app_runner)
