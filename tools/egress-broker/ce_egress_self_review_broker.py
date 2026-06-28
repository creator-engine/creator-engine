#!/usr/bin/env python3
"""Host-side Unix-socket self-review broker for governed CE seats.

The seat submits value-only PR review intent over a Unix socket:
``{seat_id, pr_number, head_sha, event, body, reviewer_authority_envelope?}``.
The host broker validates the bounded JSON request, gates ``APPROVE`` by role +
run-mode + reviewer-authority-envelope policy, mints a short-lived repo-scoped
review credential outside the sandbox only after the author≠reviewer check,
injects it only into the trusted host ``gh api`` subprocess environment, and
returns a secret-free JSON result.

Protocol: one connection carries one JSON object. The client half-closes after
writing; the broker responds with one JSON object and closes.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import socket
import socketserver
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

# Match ce_egress_broker.py: make sibling package + validators importable when
# run directly from an operator shell.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
_VALIDATORS = os.path.join(_REPO_ROOT, "validators")
if os.path.isdir(_VALIDATORS):
    sys.path.insert(0, _VALIDATORS)

from creator_engine_validator.forge.cred_injection_proxy import (  # noqa: E402
    ContainedSeatReview,
    CredentialBinding,
    CredentialProxyRefused,
    submit_contained_seat_pr_review,
    validate_approve_authority,
)
from creator_engine_validator.forge.scoped_token import ScopedToken, TokenRequest  # noqa: E402
from egress_broker.config import BrokerConfig, BrokerConfigError, SeatAppConfig, load_broker_config  # noqa: E402
from egress_broker.host_broker import systemd_activated_unix_socket  # noqa: E402
from egress_broker.minter import (  # noqa: E402
    EgressSignerError,
    VaultKvConfig,
    make_signer_for_seat,
    mint_egress_token,
    resolve_installation_id,
)
from egress_broker.orchestrator import policy_binding_sha  # noqa: E402

try:
    from creator_engine_validator.grading_policy import RunMode as _RunMode  # noqa: E402
except ImportError:
    _RunMode = None  # type: ignore[assignment,misc]

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_CONFIG_ERROR = 3

_APPROLE_LOGIN_TIMEOUT_S = 10.0

DEFAULT_SOCKET = "/tmp/ce-egress-self-review.sock"
DEFAULT_MAX_REQUEST_BYTES = 64 * 1024
REVIEW_PERMISSIONS = {"metadata": "read", "pull_requests": "write"}
REVIEW_TTL_SECONDS = 600
REVIEW_SECRET_NAME = "forge_self_review"
ALLOWED_EVENTS = frozenset({"COMMENT", "REQUEST_CHANGES"})
STRANGELOOP_ALLOWED_EVENTS = ALLOWED_EVENTS | frozenset({"APPROVE"})

_RE_HEAD_SHA = re.compile(r"^[0-9a-fA-F]{40,64}$")
_LOG = logging.getLogger("ce-egress-self-review")


class SelfReviewRefused(Exception):
    """Fail-closed refusal before or during host-side review submission."""


class _BrokerStartupError(Exception):
    """Fail-closed startup error; message is safe to print (no secrets)."""


def _is_strangeloop(run_mode: str | None) -> bool:
    """Return True only when run_mode is explicitly the strangeLoop value."""
    if run_mode is None:
        return False
    if _RunMode is not None:
        return run_mode == _RunMode.STRANGE_LOOP.value
    return run_mode == "strangeLoop"


def _allowed_events(run_mode: str | None) -> frozenset[str]:
    if _is_strangeloop(run_mode):
        return STRANGELOOP_ALLOWED_EVENTS
    return ALLOWED_EVENTS


def _event_refusal_message(run_mode: str | None) -> str:
    if _is_strangeloop(run_mode):
        return "review event must be COMMENT, REQUEST_CHANGES, or APPROVE"
    return "review event must be COMMENT or REQUEST_CHANGES"


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

    Copied verbatim from the merged self-PUSH broker (ce-ops#267) so both credential
    paths share identical security properties.
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


def _build_signer(seat: SeatAppConfig, *, env: dict[str, str] | None = None):
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

    Mirrors the merged self-PUSH broker (ce-ops#267) exactly.
    """
    e = env if env is not None else dict(os.environ)

    if seat.secret_ref is not None:
        # --- Vault-backed path (ce-ops#268, mirrors #267) ---
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
            f"[ce-egress-self-review] seat {seat.seat_id!r}: vault-backed signer initialised",
            file=sys.stderr,
        )
        return make_signer_for_seat(seat, vault_config=vault_cfg)

    # --- PEM-backed path (legacy) ---
    print(
        f"[ce-egress-self-review] seat {seat.seat_id!r}: pem-backed signer initialised",
        file=sys.stderr,
    )
    return make_signer_for_seat(seat, vault_config=None)


def _resolve_pr_author(repo: str, pr_number: int) -> str:
    """Resolve the PR author login host-side via a read-only ``gh api`` call.

    Mirrors the author-resolution idiom in ``forge/plan_approval.py`` and
    ``forge/review_pickup.py`` (``repos/{repo}/pulls/{pr}`` → ``.user.login``)
    so the author≠reviewer invariant is enforced consistently. The read uses
    the host's ambient ``gh`` credentials — it runs BEFORE any scoped review
    credential is minted, exactly like the APPROVE refusal.

    Fails CLOSED: any transport/parse failure, a non-zero exit, or a missing
    login raises :class:`SelfReviewRefused`. The author is never trusted from
    the (untrusted) contained-seat request; it is resolved at the source host.
    """
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{repo}/pulls/{pr_number}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SelfReviewRefused(
            f"could not resolve PR author for {repo}#{pr_number}; refusing fail-closed"
        ) from exc
    if proc.returncode != 0:
        raise SelfReviewRefused(
            f"could not resolve PR author for {repo}#{pr_number}; refusing fail-closed"
        )
    try:
        pr_obj = json.loads(proc.stdout or "")
    except (json.JSONDecodeError, ValueError) as exc:
        raise SelfReviewRefused(
            f"could not parse PR author for {repo}#{pr_number}; refusing fail-closed"
        ) from exc
    login = ""
    if isinstance(pr_obj, Mapping):
        login = str(((pr_obj.get("user") or {}) if isinstance(pr_obj.get("user"), Mapping) else {}).get("login") or "").strip()
    if not login:
        raise SelfReviewRefused(
            f"PR author login empty for {repo}#{pr_number}; refusing fail-closed"
        )
    return login


@dataclass(frozen=True)
class SelfReviewRequest:
    """Value-only request accepted from the governed seat."""

    seat_id: str
    pr_number: int
    head_sha: str
    event: str
    body: str = ""
    reviewer_authority_envelope: Mapping[str, Any] | None = None
    containment_substrate: str | None = None


@dataclass(frozen=True)
class SelfReviewResult:
    """Secret-free response returned to the contained seat/client."""

    ok: bool
    repo: str
    pr_number: int
    head_sha: str
    event: str
    review_id: int | None
    applied: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "repo": self.repo,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "event": self.event,
            "review_id": self.review_id,
            "applied": self.applied,
        }


def parse_request(payload: Mapping[str, Any], run_mode: str | None = None) -> SelfReviewRequest:
    """Validate the bounded JSON object into a value-only request.

    This performs the run-mode/envelope APPROVE shape check before any caller
    can resolve/mint or invoke a source-host transport.
    """
    if not isinstance(payload, Mapping):
        raise SelfReviewRefused("request must be a JSON object")
    seat_id = str(payload.get("seat_id") or "").strip()
    if not seat_id:
        raise SelfReviewRefused("request missing non-empty seat_id")
    try:
        pr_number = int(payload.get("pr_number"))
    except (TypeError, ValueError):
        raise SelfReviewRefused("request pr_number must be an integer") from None
    if pr_number <= 0:
        raise SelfReviewRefused("request pr_number must be positive")
    head_sha = str(payload.get("head_sha") or "").strip()
    if not _RE_HEAD_SHA.match(head_sha):
        raise SelfReviewRefused("request head_sha must be a 40-64 hex commit id")
    event = str(payload.get("event") or "").strip().upper()
    if event == "APPROVE" and not _is_strangeloop(run_mode):
        raise SelfReviewRefused("APPROVE is controller approval-wall only; host broker refuses it")
    if event not in _allowed_events(run_mode):
        raise SelfReviewRefused(_event_refusal_message(run_mode))
    body = str(payload.get("body") or "")
    reviewer_authority_envelope = _request_reviewer_authority_envelope(payload)
    containment_substrate = (
        str(payload.get("containment_substrate")).strip()
        if payload.get("containment_substrate") is not None
        else None
    )
    if event == "APPROVE":
        try:
            validate_approve_authority(
                run_mode=run_mode,
                reviewer_authority_envelope=reviewer_authority_envelope,
                pr_number=pr_number,
                head_sha=head_sha,
            )
        except CredentialProxyRefused as exc:
            raise SelfReviewRefused(str(exc)) from exc
    return SelfReviewRequest(
        seat_id=seat_id,
        pr_number=pr_number,
        head_sha=head_sha,
        event=event,
        body=body,
        reviewer_authority_envelope=reviewer_authority_envelope,
        containment_substrate=containment_substrate,
    )


def _request_reviewer_authority_envelope(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for key in ("reviewer_authority_envelope", "reviewer_authority"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def bounded_json_load(data: bytes, *, max_bytes: int = DEFAULT_MAX_REQUEST_BYTES) -> Mapping[str, Any]:
    """Parse a single bounded JSON request body."""
    if len(data) > max_bytes:
        raise SelfReviewRefused(f"request exceeds max_request_bytes={max_bytes}")
    if not data.strip():
        raise SelfReviewRefused("empty request")
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise SelfReviewRefused(f"malformed JSON request: {exc}") from exc
    if not isinstance(obj, Mapping):
        raise SelfReviewRefused("request must be a JSON object")
    return obj


def submit_self_review(
    request: SelfReviewRequest,
    *,
    config: BrokerConfig,
    signer=None,
    transport=None,
    gh_spawn=None,
    now: Callable[[], float] | None = None,
    resolve_id_fn: Callable[[SeatAppConfig], int] | None = None,
    mint_fn: Callable[[TokenRequest], ScopedToken] | None = None,
    resolve_author_fn: Callable[[str, int], str] | None = None,
    run_mode: str | None = None,
) -> SelfReviewResult:
    """Mint a scoped review credential and submit a governed PR review via ``gh api``.

    The request is assumed to have passed :func:`parse_request`; this function
    re-checks the event as defense-in-depth before source-host write calls.
    Credentials are env-only through ``authenticated_gh_runner`` inside the
    existing credential-injection proxy helper.

    Before minting any credential the broker enforces the **author≠reviewer**
    invariant (mirroring ``forge/plan_approval.py`` /
    ``forge/review_pickup.py``): the PR author is resolved host-side and a seat
    is refused if it is the PR's own author — no seat may review a PR it wrote,
    for ANY event (COMMENT / REQUEST_CHANGES / gated APPROVE). Author resolution
    fails CLOSED.
    """
    if request.event not in _allowed_events(run_mode):
        raise SelfReviewRefused(_event_refusal_message(run_mode))

    try:
        seat = config.seat(request.seat_id)
    except BrokerConfigError as exc:
        raise SelfReviewRefused(str(exc)) from exc

    # Author≠reviewer guard. Positioned with the APPROVE refusal — BEFORE any
    # installation/credential minting or source-host write. The seat's review
    # identity is the App owner it mints + posts AS (``seat.app_owner``), the
    # same login GitHub records as the review's author; compare it to the PR's
    # resolved author. Resolution fails closed (refuse, never post).
    resolve_author = resolve_author_fn or _resolve_pr_author
    pr_author = resolve_author(config.repo, request.pr_number)
    if pr_author and pr_author == seat.app_owner:
        raise SelfReviewRefused(
            "self-review refused: requesting seat is the PR author "
            "(author≠reviewer invariant)"
        )

    if request.event == "APPROVE":
        try:
            validate_approve_authority(
                run_mode=run_mode,
                reviewer_authority_envelope=request.reviewer_authority_envelope,
                pr_number=request.pr_number,
                head_sha=request.head_sha,
            )
        except CredentialProxyRefused as exc:
            raise SelfReviewRefused(str(exc)) from exc

    # Signer selection (ce-ops#268): an injected ``signer`` (tests, back-compat)
    # wins. Otherwise route by the seat's key source — secret_ref → vault-backed
    # signer (per-call AppRole login + OpenBao KV fetch, RAM-only); pem_path →
    # openssl signer. Vault-backed seats with missing env fail closed in
    # ``_build_signer`` (never fall back to disk); that fail-closed startup error
    # is surfaced as a refusal (no secrets in the message) rather than crashing
    # the per-request handler.
    if signer is not None:
        active_signer = signer
    else:
        try:
            active_signer = _build_signer(seat)
        except _BrokerStartupError as exc:
            raise SelfReviewRefused(str(exc)) from exc
    resolver = resolve_id_fn or (
        lambda s: resolve_installation_id(
            s,
            installation_owner=config.installation_owner,
            signer=active_signer,
            transport=transport,
            now=now,
        )
    )
    installation_id = resolver(seat)
    run_id = f"self-review-{request.seat_id}-{request.head_sha[:12]}-pr{request.pr_number}"
    policy_sha = policy_binding_sha(config)

    def _default_minter(token_request: TokenRequest) -> ScopedToken:
        return mint_egress_token(
            replace(seat, installation_id=token_request.installation_id),
            repo=token_request.repo,
            installation_owner=config.installation_owner,
            signer=active_signer,
            run_id=token_request.run_id,
            policy_sha=token_request.policy_sha,
            permissions=token_request.permissions,
            escalation_authority=token_request.escalation_authority,
            ttl_seconds=token_request.requested_ttl_seconds,
            secret_name=token_request.secret_name,
            transport=transport,
            now=now,
        )

    binding = CredentialBinding(
        installation_id=installation_id,
        run_id=run_id,
        policy_sha=policy_sha,
        permissions=REVIEW_PERMISSIONS,
        secret_name=REVIEW_SECRET_NAME,
        requested_ttl_seconds=REVIEW_TTL_SECONDS,
    )

    try:
        submitted = submit_contained_seat_pr_review(
            ContainedSeatReview(
                seat_id=request.seat_id,
                repo=config.repo,
                pr_number=request.pr_number,
                head_sha=request.head_sha,
                event=request.event,
                body=request.body,
                run_mode=run_mode,
                reviewer_authority_envelope=request.reviewer_authority_envelope,
                containment_substrate=request.containment_substrate,
            ),
            binding=binding,
            minter=mint_fn or _default_minter,
            durable_metadata={"broker": "ce_egress_self_review_broker"},
            token_spawn=gh_spawn,
        )
    except CredentialProxyRefused as exc:
        raise SelfReviewRefused(str(exc)) from exc

    result = SelfReviewResult(
        ok=True,
        repo=submitted.repo,
        pr_number=submitted.pr_number,
        head_sha=submitted.head_sha,
        event=submitted.event,
        review_id=submitted.review_id,
        applied=submitted.applied,
    )
    _LOG.info(
        "submitted self-review seat=%s repo=%s pr=%s event=%s review_id=%s",
        request.seat_id,
        result.repo,
        result.pr_number,
        result.event,
        result.review_id,
    )
    return result


def _read_bounded_from_socket(conn: socket.socket, *, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    seen = 0
    while True:
        chunk = conn.recv(min(8192, max_bytes + 1 - seen))
        if not chunk:
            break
        chunks.append(chunk)
        seen += len(chunk)
        if seen > max_bytes:
            raise SelfReviewRefused(f"request exceeds max_request_bytes={max_bytes}")
    return b"".join(chunks)


class _ReviewHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server: SelfReviewServer = self.server  # type: ignore[assignment]
        try:
            raw = _read_bounded_from_socket(self.request, max_bytes=server.max_request_bytes)
            payload = bounded_json_load(raw, max_bytes=server.max_request_bytes)
            request = parse_request(payload, run_mode=server.run_mode)
            result = server.submitter(request)
            response: dict[str, object] = result.to_dict()
            status = "ok"
        except SelfReviewRefused as exc:
            response = {"ok": False, "error": str(exc)}
            status = "refused"
        except Exception:
            _LOG.exception("self-review broker internal error")
            response = {"ok": False, "error": "internal broker error"}
            status = "error"
        _LOG.info("request %s", status)
        self.request.sendall(json.dumps(response, sort_keys=True).encode("utf-8") + b"\n")


class SelfReviewServer(socketserver.UnixStreamServer):
    """Unix-stream server carrying broker config and injectable submitter."""

    allow_reuse_address = True

    def __init__(
        self,
        socket_path: str,
        *,
        submitter: Callable[[SelfReviewRequest], SelfReviewResult],
        max_request_bytes: int,
        activated_socket: socket.socket | None = None,
        run_mode: str | None = None,
    ) -> None:
        self.socket_path = socket_path
        self.submitter = submitter
        self.max_request_bytes = max_request_bytes
        self.run_mode = run_mode
        self._owns_socket_path = activated_socket is None
        if activated_socket is None:
            Path(socket_path).parent.mkdir(parents=True, exist_ok=True)
            try:
                Path(socket_path).unlink()
            except FileNotFoundError:
                pass
            super().__init__(socket_path, _ReviewHandler)
            os.chmod(socket_path, 0o600)
        else:
            super().__init__(socket_path, _ReviewHandler, bind_and_activate=False)
            self.socket.close()
            self.socket = activated_socket

    def server_close(self) -> None:
        super().server_close()
        if not self._owns_socket_path:
            return
        try:
            Path(self.socket_path).unlink()
        except FileNotFoundError:
            pass


def serve(
    *,
    socket_path: str,
    config: BrokerConfig,
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES,
    signer=None,
    transport=None,
    gh_spawn=None,
    now: Callable[[], float] | None = None,
    activated_socket: socket.socket | None = None,
    run_mode: str | None = None,
) -> None:
    """Serve the Unix socket until interrupted."""
    def submitter(request: SelfReviewRequest) -> SelfReviewResult:
        return submit_self_review(
            request,
            config=config,
            signer=signer,
            transport=transport,
            gh_spawn=gh_spawn,
            now=now,
            run_mode=run_mode,
        )

    with SelfReviewServer(
        socket_path,
        submitter=submitter,
        max_request_bytes=max_request_bytes,
        activated_socket=activated_socket,
        run_mode=run_mode,
    ) as server:
        _LOG.info("listening socket=%s repo=%s", socket_path, config.repo)
        server.serve_forever()


def send_request(socket_path: str, request: SelfReviewRequest, *, timeout: float = 30.0) -> dict[str, object]:
    """Small client helper used by the opt-in live smoke mode."""
    request_payload: dict[str, object] = {
        "seat_id": request.seat_id,
        "pr_number": request.pr_number,
        "head_sha": request.head_sha,
        "event": request.event,
        "body": request.body,
    }
    if request.reviewer_authority_envelope is not None:
        request_payload["reviewer_authority_envelope"] = dict(request.reviewer_authority_envelope)
    if request.containment_substrate is not None:
        request_payload["containment_substrate"] = request.containment_substrate
    payload = json.dumps(request_payload, sort_keys=True).encode("utf-8")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(socket_path)
        client.sendall(payload)
        client.shutdown(socket.SHUT_WR)
        data = bytearray()
        while True:
            chunk = client.recv(8192)
            if not chunk:
                break
            data.extend(chunk)
    parsed = json.loads(bytes(data).decode("utf-8"))
    if not isinstance(parsed, dict):
        raise SelfReviewRefused("broker returned non-object JSON")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ce-egress-self-review-broker",
        description="Host-side Unix-socket broker for governed COMMENT/REQUEST_CHANGES PR reviews.",
    )
    parser.add_argument("--socket", default=DEFAULT_SOCKET, help="Unix socket path")
    parser.add_argument("--config", help="broker config JSON path (required for daemon mode)")
    parser.add_argument("--max-request-bytes", type=int, default=DEFAULT_MAX_REQUEST_BYTES)
    parser.add_argument("--verbose", action="store_true", help="enable INFO logging")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--serve", action="store_true", help="run the host daemon (default)")
    mode.add_argument(
        "--send-comment",
        action="store_true",
        help="opt-in smoke client: submit one COMMENT request to a running daemon",
    )
    mode.add_argument(
        "--send-request-changes",
        action="store_true",
        help="opt-in smoke client: submit one REQUEST_CHANGES request to a running daemon",
    )
    parser.add_argument("--seat", help="seat id for smoke client")
    parser.add_argument("--pr-number", type=int, help="PR number for smoke client")
    parser.add_argument("--head-sha", help="PR head SHA for smoke client")
    parser.add_argument("--body", default="", help="review body for smoke client")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="[ce-egress-self-review] %(levelname)s %(message)s",
    )
    if args.max_request_bytes <= 0:
        print("[ce-egress-self-review] config error: --max-request-bytes must be positive", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    if args.send_comment or args.send_request_changes:
        event = "COMMENT" if args.send_comment else "REQUEST_CHANGES"
        try:
            request = parse_request(
                {
                    "seat_id": args.seat,
                    "pr_number": args.pr_number,
                    "head_sha": args.head_sha,
                    "event": event,
                    "body": args.body,
                }
            )
            print(json.dumps(send_request(args.socket, request), sort_keys=True))
            return EXIT_OK
        except (OSError, SelfReviewRefused, json.JSONDecodeError) as exc:
            print(f"[ce-egress-self-review] REFUSED (fail-closed): {exc}", file=sys.stderr)
            return EXIT_REFUSED

    if not args.config:
        print("[ce-egress-self-review] config error: --config is required for --serve", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        config = load_broker_config(args.config)
    except BrokerConfigError as exc:
        print(f"[ce-egress-self-review] config error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    try:
        serve(
            socket_path=args.socket,
            config=config,
            max_request_bytes=args.max_request_bytes,
            activated_socket=systemd_activated_unix_socket(),
        )
    except KeyboardInterrupt:
        return EXIT_OK
    except _BrokerStartupError as exc:
        # Fail-closed vault misconfiguration (no secrets in the message).
        print(f"[ce-egress-self-review] startup error: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except (OSError, RuntimeError) as exc:
        print(f"[ce-egress-self-review] REFUSED (fail-closed): {exc}", file=sys.stderr)
        return EXIT_REFUSED
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
