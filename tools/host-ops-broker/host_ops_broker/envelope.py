"""Request and response envelope helpers for host-ops broker v1."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from host_ops_broker.verb_schema import MUTATING_VERBS, VERBS, reject_command_like_keys, validate_params

REQUEST_SCHEMA = "ce.host_ops.request.v1"
RESPONSE_SCHEMA = "ce.host_ops.response.v1"
RESULTS = frozenset(
    {"ok", "already-converged", "refused", "rate-limited", "disabled", "failed", "degraded"}
)


class EnvelopeError(ValueError):
    """The request or response envelope is malformed."""


@dataclass(frozen=True)
class Caller:
    identity: str
    role: str
    work_claim: str | None = None


@dataclass(frozen=True)
class RequestEnvelope:
    schema: str
    verb: str
    request_id: str
    caller: Caller
    params: dict[str, Any]
    reason: str | None
    created_at: str


def utc_z(dt: datetime) -> str:
    """Return an RFC3339 UTC timestamp with a trailing ``Z``."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat(timespec="seconds") + "Z"


def now_utc_z() -> str:
    return utc_z(datetime.now(timezone.utc))


def is_rfc3339_utc_z(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    body = value[:-1]
    if not body:
        return False
    try:
        parsed = datetime.fromisoformat(body + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _require_mapping(value: object, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EnvelopeError(f"{where} must be an object")
    return value


def _require_str(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnvelopeError(f"{where} must be a non-empty string")
    return value


def _reject_extra_keys(raw: Mapping[str, Any], allowed: set[str], where: str) -> None:
    extra = sorted(set(str(k) for k in raw) - allowed)
    if extra:
        raise EnvelopeError(f"{where} has unsupported field(s): {', '.join(extra)}")


def validate_request(raw: object) -> RequestEnvelope:
    """Validate and normalize a host-ops request envelope."""
    env = _require_mapping(raw, "request")
    reject_command_like_keys(env)
    _reject_extra_keys(env, {"schema", "verb", "request_id", "caller", "params", "reason", "created_at"}, "request")

    schema = _require_str(env.get("schema"), "schema")
    if schema != REQUEST_SCHEMA:
        raise EnvelopeError(f"schema must be {REQUEST_SCHEMA!r}")
    verb = _require_str(env.get("verb"), "verb")
    if verb not in VERBS:
        raise EnvelopeError(f"verb {verb!r} is not supported")
    request_id = _require_str(env.get("request_id"), "request_id")

    caller_raw = _require_mapping(env.get("caller"), "caller")
    reject_command_like_keys(caller_raw)
    _reject_extra_keys(caller_raw, {"identity", "role", "work_claim"}, "caller")
    identity = _require_str(caller_raw.get("identity"), "caller.identity")
    role = _require_str(caller_raw.get("role"), "caller.role")
    work_claim_raw = caller_raw.get("work_claim")
    work_claim = None
    if work_claim_raw is not None:
        work_claim = _require_str(work_claim_raw, "caller.work_claim")

    if "params" not in env:
        raise EnvelopeError("params is required")
    params = validate_params(verb, env.get("params"))

    reason_raw = env.get("reason")
    reason = None
    if reason_raw is not None:
        reason = _require_str(reason_raw, "reason")
    if verb in MUTATING_VERBS and reason is None:
        raise EnvelopeError(f"reason is required for mutating verb {verb!r}")

    created_at = _require_str(env.get("created_at"), "created_at")
    if not is_rfc3339_utc_z(created_at):
        raise EnvelopeError("created_at must be RFC3339 UTC with trailing Z")

    return RequestEnvelope(
        schema=schema,
        verb=verb,
        request_id=request_id,
        caller=Caller(identity=identity, role=role, work_claim=work_claim),
        params=params,
        reason=reason,
        created_at=created_at,
    )


def response_envelope(
    request_id: str,
    verb: str,
    result: str,
    *,
    changed: bool = False,
    evidence_ref: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if result not in RESULTS:
        raise EnvelopeError(f"result {result!r} is not supported")
    return {
        "schema": RESPONSE_SCHEMA,
        "request_id": request_id,
        "verb": verb,
        "result": result,
        "changed": bool(changed),
        "evidence_ref": evidence_ref,
        "details": dict(details or {}),
    }
