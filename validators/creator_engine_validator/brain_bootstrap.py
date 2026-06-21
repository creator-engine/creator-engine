"""Deterministic Knowledge-SSOT bootstrap projection.

This module is deliberately read-only. It reuses ``brain_runtime`` as the
single source of truth for ledger parsing and hash-chain validation, then
projects the current active assertions into a JSON-serializable bootstrap
payload for a controller/foreman seat. It does not contact a network, open a
datastore, use MCP, or migrate any memory substrate.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from . import brain_runtime
from ._versions import V3_LOCAL_STATE_ROOT
from .runtime_evidence_spine import CONTENT_HASH_FIELD
from .seat_class import resolve_seat_class

BOOTSTRAP_KIND = "brain-bootstrap-context"
BOOTSTRAP_SCHEMA_VERSION = "1"
DEFAULT_ROLE = "controller"
DEFAULT_SEAT_CLASS = "foreman"
GLOBAL_SCOPE = "global"
BOOTSTRAP_REF_ENV = "CE_BRAIN_BOOTSTRAP_REF"
BOOTSTRAP_SHA256_ENV = "CE_BRAIN_BOOTSTRAP_SHA256"


class BrainBootstrapRefused(brain_runtime.BrainRuntimeError):
    code = "CE-BRAIN-BOOTSTRAP-REFUSED"

    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
        errors: Sequence[str] | None = None,
    ):
        self.cause = cause
        self.errors = tuple(errors or ())
        super().__init__(message)


@dataclass(frozen=True)
class BootstrapRequest:
    scope: str | dict[str, Any] | None = None
    role: str = DEFAULT_ROLE
    seat_class: str | None = DEFAULT_SEAT_CLASS
    state_root: Path | str = V3_LOCAL_STATE_ROOT


def build_bootstrap_payload(
    *,
    scope: str | dict[str, Any] | None = None,
    role: str = DEFAULT_ROLE,
    seat_class: str | None = DEFAULT_SEAT_CLASS,
    state_root: Path | str = V3_LOCAL_STATE_ROOT,
) -> dict[str, Any]:
    """Return a deterministic JSON-serializable controller bootstrap payload.

    Missing or invalid ledgers refuse fail-closed before any payload is
    returned.
    """

    request = BootstrapRequest(scope=scope, role=role, seat_class=seat_class, state_root=state_root)
    return bootstrap(request)


def payload_bytes(payload: dict[str, Any]) -> bytes:
    """Canonical bytes for the launch-injected bootstrap payload."""

    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def payload_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(payload_bytes(payload)).hexdigest()


def write_payload(path: Path | str, payload: dict[str, Any]) -> str:
    """Write the payload atomically and return the reproduced SHA256."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = payload_bytes(payload)
    digest = hashlib.sha256(content).hexdigest()
    tmp = target.parent / f"{target.name}.tmp.{os.getpid()}"
    tmp.write_bytes(content)
    tmp.rename(target)
    return digest


def payload_env(path: Path | str, sha256: str) -> dict[str, str]:
    return {
        BOOTSTRAP_REF_ENV: str(Path(path)),
        BOOTSTRAP_SHA256_ENV: str(sha256),
    }


def bootstrap(request: BootstrapRequest) -> dict[str, Any]:
    role = _require_non_empty_string("role", request.role)
    seat_class = resolve_seat_class(request.seat_class)
    normalized_scope = _normalize_scope(request.scope, role=role, seat_class=seat_class)
    ledger_path = brain_runtime.ledger_path(request.state_root)

    verified = brain_runtime.verify_ledger(request.state_root)
    if not verified.ok:
        raise BrainBootstrapRefused(
            "brain bootstrap refused invalid or missing assertion ledger",
            errors=verified.errors,
        )
    try:
        records = brain_runtime.load_records(request.state_root)
    except brain_runtime.BrainLedgerInvalid as exc:
        raise BrainBootstrapRefused(
            "brain bootstrap refused invalid assertion ledger",
            cause=exc,
            errors=tuple(_render_error(error) for error in getattr(exc, "errors", ())),
        ) from exc

    active = _active_current_view(records)
    relevant = [record for record in active if _scope_relevant(record.get("scope"), normalized_scope)]
    assertions = [_project_assertion(record) for record in relevant]
    assertions.sort(key=lambda item: (item["sequence"], item["id"]))

    payload = {
        "kind": BOOTSTRAP_KIND,
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "context": {
            "role": role,
            "seat_class": seat_class,
            "scope": normalized_scope,
        },
        "knowledge_ssot": {
            "ledger_path": str(ledger_path),
            "record_count": len(records),
            "active_count": len(active),
            "scope_relevant_count": len(assertions),
            "head_content_hash": _head_content_hash(records),
            "assertions": assertions,
        },
    }
    _assert_json_serializable(payload)
    return payload


def _require_non_empty_string(name: str, value: str) -> str:
    if not isinstance(value, str) or not value:
        raise BrainBootstrapRefused(f"{name} must be a non-empty string")
    return value


def _normalize_scope(
    scope: str | dict[str, Any] | None,
    *,
    role: str,
    seat_class: str,
) -> str | dict[str, Any]:
    if scope is None:
        return {"role": role, "seat_class": seat_class}
    try:
        normalized = copy.deepcopy(brain_runtime._normalize_scope(scope))  # type: ignore[attr-defined]
    except brain_runtime.BrainAssertionRefused as exc:
        raise BrainBootstrapRefused("bootstrap scope must be a non-empty string or mapping", cause=exc) from exc
    if isinstance(normalized, dict):
        normalized["role"] = role
        normalized["seat_class"] = seat_class
    return normalized


def _active_current_view(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        rid = record.get("id")
        if isinstance(rid, str):
            latest[rid] = record
    return [copy.deepcopy(record) for record in latest.values() if record.get("status") == "active"]


def _scope_relevant(assertion_scope: Any, requested_scope: str | dict[str, Any]) -> bool:
    if assertion_scope == requested_scope:
        return True
    if assertion_scope == GLOBAL_SCOPE:
        return True
    if isinstance(assertion_scope, dict) and isinstance(requested_scope, dict):
        return _mapping_scope_applies(assertion_scope, requested_scope)
    return False


def _mapping_scope_applies(assertion_scope: dict[str, Any], requested_scope: dict[str, Any]) -> bool:
    for key, value in assertion_scope.items():
        if key not in requested_scope:
            return False
        if requested_scope[key] != value:
            return False
    return True


def _project_assertion(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record["id"]),
        "claim": copy.deepcopy(record["claim"]),
        "scope": copy.deepcopy(record["scope"]),
        "evidence_ref": str(record["evidence_ref"]),
        "sequence": int(record["sequence"]),
        "content_hash": str(record[CONTENT_HASH_FIELD]),
    }


def _head_content_hash(records: Sequence[dict[str, Any]]) -> str | None:
    if not records:
        return None
    return str(records[-1][CONTENT_HASH_FIELD])


def _assert_json_serializable(payload: dict[str, Any]) -> None:
    try:
        json.dumps(payload, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise BrainBootstrapRefused("brain bootstrap payload must be JSON-serializable", cause=exc) from exc


def _render_error(error: Any) -> str:
    formatter = getattr(error, "format", None)
    if callable(formatter):
        return str(formatter())
    return str(error)
