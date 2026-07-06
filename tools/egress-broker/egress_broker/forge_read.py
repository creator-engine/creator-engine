"""Host-side forge read lane for contained CE seats.

The contained seat supplies only values: seat id, read verb, repo, and issue/PR
number. The broker resolves the seat App host-side, enforces the per-seat rate
cap from the broker policy, mints a short-lived read-only installation token at
request time, runs one trusted ``gh api`` read with the token in the child env
only, revokes the token, and appends a secret-free audit line for allow/refuse.

Out of scope for this slice:

* ``kind:own`` solo parity. The seam is :data:`KIND_OWN_PARITY_STATUS`; a later
  slice can route that mode without changing the broker read request shape.
* Governed ``web-fetch``. This module intentionally exposes forge reads only.
"""
from __future__ import annotations

import fcntl
import json
import re
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from creator_engine_validator.forge._redact import redact_gh_stderr
from creator_engine_validator.forge.credential_runner import authenticated_gh_runner
from creator_engine_validator.forge.github_repo_config import ForgeConfigError, ForgeConfigRefused
from creator_engine_validator.forge.scoped_token import ScopedToken, TokenRequest, revoke_scoped_token
from egress_broker.audit import append_audit, count_recent_forge_reads
from egress_broker.config import BrokerConfig, BrokerConfigError, SeatAppConfig
from egress_broker.minter import mint_egress_token, resolve_installation_id
from egress_broker.orchestrator import policy_binding_sha

READ_PERMISSIONS = {"metadata": "read", "issues": "read", "pull_requests": "read"}
READ_ESCALATION: tuple[tuple[str, str], ...] = ()
READ_TTL_SECONDS = 300
READ_SECRET_NAME = "forge_egress_read"
KIND_OWN_PARITY_STATUS = "deferred: kind:broker implemented; kind:own routes in a later slice"
WEB_FETCH_STATUS = "deferred: governed web-fetch is a later egress-broker slice"

_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_WRITEISH_FIELDS = frozenset(
    {
        "body",
        "command",
        "data",
        "event",
        "input",
        "method",
        "mutation",
        "patch",
        "payload",
        "permissions",
        "query",
        "ref",
        "refspec",
        "remote",
        "state",
        "token",
    }
)
_LOCK_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")


class ForgeReadRefused(Exception):
    """A fail-closed forge-read refusal carrying the audit record."""

    def __init__(self, message: str, *, audit_record: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.audit_record = dict(audit_record or {})


@dataclass(frozen=True)
class ForgeReadRequest:
    """Value-only forge read request accepted from a governed seat."""

    seat_id: str
    verb: str
    repo: str
    number: int

    @property
    def resource(self) -> str:
        return f"{self.repo}#{self.number}"


@dataclass(frozen=True)
class ForgeReadResult:
    """Secret-free JSON response for a brokered forge read."""

    ok: bool
    seat_id: str
    verb: str
    repo: str
    number: int
    resource: str
    request_path: str
    body: object
    metadata: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "seat_id": self.seat_id,
            "verb": self.verb,
            "repo": self.repo,
            "number": self.number,
            "resource": self.resource,
            "request_path": self.request_path,
            "body": self.body,
            "metadata": dict(self.metadata),
        }


def _now_iso(now: Callable[[], datetime] | None) -> str:
    dt = (now or (lambda: datetime.now(timezone.utc)))()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _resource_for(payload: Mapping[str, Any] | None, request: ForgeReadRequest | None) -> str:
    if request is not None:
        return request.resource
    if not isinstance(payload, Mapping):
        return "unknown"
    repo = str(payload.get("repo") or "").strip() or "unknown"
    number = str(payload.get("number") or "").strip() or "unknown"
    return f"{repo}#{number}"


def _audit(
    config: BrokerConfig,
    *,
    payload: Mapping[str, Any] | None = None,
    request: ForgeReadRequest | None = None,
    decision: str,
    reason: str | None = None,
    request_path: str | None = None,
    status: int | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    seat_id = (
        request.seat_id
        if request is not None
        else str((payload or {}).get("seat_id") or "").strip()
    )
    repo = request.repo if request is not None else str((payload or {}).get("repo") or "").strip()
    verb = request.verb if request is not None else str((payload or {}).get("verb") or "").strip()
    record: dict[str, Any] = {
        "event": "forge_read",
        "seat_id": seat_id,
        "repo": repo,
        "resource": _resource_for(payload, request),
        "verb": verb,
        "decision": decision,
        "requested_at": _now_iso(now),
    }
    if request is not None:
        record["number"] = request.number
    if request_path:
        record["request_path"] = request_path
    if status is not None:
        record["status"] = status
    if reason:
        record["reason"] = reason
    return append_audit(config.audit_log, record, now=now)


def _forge_read_lock_path(config: BrokerConfig, seat_id: str) -> Path:
    audit_path = Path(config.audit_log).expanduser()
    safe_seat = _LOCK_SAFE_RE.sub("_", seat_id).strip("._") or "unknown"
    return audit_path.with_name(f"{audit_path.name}.{safe_seat}.forge-read.lock")


@contextmanager
def _forge_read_rate_lock(config: BrokerConfig, seat_id: str):
    lock_path = _forge_read_lock_path(config, seat_id)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def parse_request(payload: Mapping[str, Any]) -> ForgeReadRequest:
    """Validate a bounded value-only forge-read request.

    The parser rejects write-shaped fields before callers can resolve, mint, or
    invoke a source-host transport.
    """
    if not isinstance(payload, Mapping):
        raise ForgeReadRefused("request must be a JSON object")
    unsupported = sorted(k for k in (str(k) for k in payload) if k in _WRITEISH_FIELDS)
    if unsupported:
        raise ForgeReadRefused(
            "forge-read request carries write-shaped fields; refusing: "
            + ", ".join(unsupported)
        )
    seat_id = str(payload.get("seat_id") or "").strip()
    if not seat_id:
        raise ForgeReadRefused("request missing non-empty seat_id")
    verb = str(payload.get("verb") or "").strip()
    if verb not in {"get-issue", "get-pr", "list-comments"}:
        raise ForgeReadRefused(
            "unsupported forge-read verb; allowed: get-issue, get-pr, list-comments"
        )
    repo = str(payload.get("repo") or "").strip()
    if not _REPO_RE.match(repo):
        raise ForgeReadRefused("request repo must be in owner/name form")
    try:
        number = int(payload.get("number"))
    except (TypeError, ValueError):
        raise ForgeReadRefused("request number must be an integer") from None
    if number <= 0:
        raise ForgeReadRefused("request number must be positive")
    return ForgeReadRequest(seat_id=seat_id, verb=verb, repo=repo, number=number)


def request_path(request: ForgeReadRequest) -> str:
    """Return the GitHub REST path for an allowed read verb."""
    if request.verb == "get-issue":
        return f"repos/{request.repo}/issues/{request.number}"
    if request.verb == "get-pr":
        return f"repos/{request.repo}/pulls/{request.number}"
    if request.verb == "list-comments":
        return f"repos/{request.repo}/issues/{request.number}/comments"
    raise ForgeReadRefused(
        "unsupported forge-read verb; allowed: get-issue, get-pr, list-comments"
    )


def _gh_get(path: str, *, gh_runner) -> tuple[object, Mapping[str, Any]]:
    proc = gh_runner(["gh", "api", "-X", "GET", path], None)
    stdout = (getattr(proc, "stdout", "") or "").strip()
    stderr = getattr(proc, "stderr", "") or ""
    if getattr(proc, "returncode", 1) != 0:
        raise ForgeReadRefused(
            f"forge read failed for {path}: {redact_gh_stderr(stderr) or 'unknown error'}"
        )
    try:
        body = json.loads(stdout) if stdout else None
    except (json.JSONDecodeError, ValueError) as exc:
        raise ForgeReadRefused(f"forge read returned non-JSON for {path}") from exc
    return body, {"status": 200}


def submit_forge_read(
    request: ForgeReadRequest,
    *,
    config: BrokerConfig,
    signer=None,
    transport=None,
    gh_spawn=None,
    now: Callable[[], float] | None = None,
    audit_now: Callable[[], datetime] | None = None,
    resolve_id_fn: Callable[[SeatAppConfig], int] | None = None,
    mint_fn: Callable[[TokenRequest], ScopedToken] | None = None,
    revoke_fn: Callable[[ScopedToken], bool] | None = None,
    gh_get_fn: Callable[[str, Any], tuple[object, Mapping[str, Any]]] | None = None,
) -> ForgeReadResult:
    """Mint a read-only token at request time and run one governed forge read."""
    try:
        seat = config.seat(request.seat_id)
    except BrokerConfigError as exc:
        raise ForgeReadRefused(str(exc)) from exc
    if request.repo != seat.repo:
        raise ForgeReadRefused(
            f"request repo {request.repo!r} does not match configured seat repo {seat.repo!r}"
        )

    cap = config.policy.max_pushes_per_window
    if cap > 0:
        recent = count_recent_forge_reads(
            config.audit_log,
            request.seat_id,
            window_seconds=config.policy.window_seconds,
            now=audit_now,
        )
        if recent >= cap:
            raise ForgeReadRefused(
                f"forge-read rate cap exceeded for seat {request.seat_id}: "
                f"{recent}/{cap} in {config.policy.window_seconds}s"
            )

    if signer is None:
        from egress_broker.minter import make_signer_for_seat

        signer = make_signer_for_seat(seat)
    resolver = resolve_id_fn or (
        lambda s: resolve_installation_id(
            s,
            installation_owner=config.installation_owner,
            signer=signer,
            transport=transport,
            now=now,
        )
    )
    installation_id = resolver(seat)
    path = request_path(request)
    run_id = f"forge-read-{request.seat_id}-{request.verb}-{request.number}"
    policy_sha = policy_binding_sha(config, repo=request.repo)

    def _default_minter(token_request: TokenRequest) -> ScopedToken:
        return mint_egress_token(
            replace(seat, installation_id=token_request.installation_id),
            repo=token_request.repo,
            installation_owner=config.installation_owner,
            signer=signer,
            run_id=token_request.run_id,
            policy_sha=token_request.policy_sha,
            permissions=token_request.permissions,
            escalation_authority=token_request.escalation_authority,
            ttl_seconds=token_request.requested_ttl_seconds,
            secret_name=token_request.secret_name,
            transport=transport,
            now=now,
        )

    token_request = TokenRequest(
        repo=request.repo,
        installation_id=installation_id,
        run_id=run_id,
        policy_sha=policy_sha,
        permissions=dict(READ_PERMISSIONS),
        secret_name=READ_SECRET_NAME,
        requested_ttl_seconds=READ_TTL_SECONDS,
        escalation_authority=READ_ESCALATION,
    )
    try:
        token = (mint_fn or _default_minter)(token_request)
        runner = authenticated_gh_runner(token, spawn=gh_spawn)
    except (ForgeConfigError, ForgeConfigRefused) as exc:
        raise ForgeReadRefused(str(exc)) from exc

    try:
        if gh_get_fn is None:
            body, metadata = _gh_get(path, gh_runner=runner)
        else:
            body, metadata = gh_get_fn(path, runner)
    finally:
        try:
            if revoke_fn is not None:
                revoke_fn(token)
            else:
                revoke_scoped_token(token, gh_runner=runner)
        except Exception:
            # The read result must not hide a successful request, but the host
            # log/audit still records no credential material. Follow-up hardening
            # can route revoke failure to a separate operational alarm.
            pass

    return ForgeReadResult(
        ok=True,
        seat_id=request.seat_id,
        verb=request.verb,
        repo=request.repo,
        number=request.number,
        resource=request.resource,
        request_path=path,
        body=body,
        metadata={
            **dict(metadata),
            "installation_id": installation_id,
            "permissions": dict(READ_PERMISSIONS),
            "kind": "broker",
        },
    )


def handle_forge_read_request(
    payload: Mapping[str, Any],
    *,
    config: BrokerConfig,
    **submit_options: Any,
) -> dict[str, Any]:
    """JSON object in, secret-free JSON object out, with audit on every outcome."""
    request: ForgeReadRequest | None = None
    audit_now = submit_options.get("audit_now")
    try:
        request = parse_request(payload)
        with _forge_read_rate_lock(config, request.seat_id):
            result = submit_forge_read(request, config=config, **submit_options)
            audit_record = _audit(
                config,
                request=request,
                decision="allow",
                request_path=result.request_path,
                status=int(result.metadata.get("status") or 200),
                now=audit_now,
            )
            out = result.to_dict()
            out["audit_record"] = audit_record
            return out
    except ForgeReadRefused as exc:
        audit_record = _audit(
            config,
            payload=payload,
            request=request,
            decision="deny",
            reason=str(exc),
            now=audit_now,
        )
        response = {
            "ok": False,
            "error": str(exc),
            "audit_record": audit_record,
        }
        return response
    except Exception as exc:
        audit_record = _audit(
            config,
            payload=payload,
            request=request,
            decision="deny",
            reason=f"internal broker error: {type(exc).__name__}",
            now=audit_now,
        )
        return {"ok": False, "error": "internal broker error", "audit_record": audit_record}


def cli_payload(verb: str, repo: str, number: int, *, seat_id: str) -> dict[str, Any]:
    """Build the value-only payload used by the CLI verbs."""
    return {"seat_id": seat_id, "verb": verb, "repo": repo, "number": number}


def default_json_dumps(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def subprocess_gh_get(path: str, runner) -> tuple[object, Mapping[str, Any]]:
    """Named live seam for tests and CLI use."""
    return _gh_get(path, gh_runner=runner)
