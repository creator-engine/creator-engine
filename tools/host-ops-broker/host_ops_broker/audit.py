"""Append-only secret-free JSONL audit for host-ops broker v1.

The forbidden-key and token-shape pattern is copied from the egress broker
instead of imported so the host-ops broker remains standalone. Timestamps use
RFC3339 UTC ``Z`` form, and the clock is injectable for deterministic tests.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from host_ops_broker.envelope import utc_z

_FORBIDDEN_KEY_SUBSTRINGS = ("token", "secret", "pem", "private_key", "app_key", "password", "value")
_TOKEN_SHAPE = re.compile(
    r"(?:gh[opusr]_|github_pat_)[A-Za-z0-9_.\-]{8,}|eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2}"
)


class AuditError(Exception):
    """Base audit failure."""


class AuditSecretLeak(AuditError):
    """A record carried credential-shaped material and was refused before write."""


def now_z(now: Callable[[], datetime] | None = None) -> str:
    dt = (now or (lambda: datetime.now(timezone.utc)))()
    return utc_z(dt)


def assert_secret_free(obj: object, *, _path: str = "") -> None:
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            key = str(k).lower()
            if any(sub in key for sub in _FORBIDDEN_KEY_SUBSTRINGS):
                raise AuditSecretLeak(
                    f"audit record key {k!r} looks like a credential; refusing to persist it"
                )
            assert_secret_free(v, _path=f"{_path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            assert_secret_free(v, _path=f"{_path}[{i}]")
    elif isinstance(obj, str) and _TOKEN_SHAPE.search(obj):
        raise AuditSecretLeak(
            f"audit record value at {_path or '<root>'} is token-shaped; refusing to persist it"
        )


def append_audit(path: str | Path, record: Mapping[str, Any]) -> dict[str, Any]:
    """Append one secret-free audit record as JSONL and return the stamped record."""
    assert_secret_free(record)
    stamped = dict(record)
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(stamped, sort_keys=True, separators=(",", ":"))
    with p.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return stamped


def build_record(
    *,
    request_id: str,
    verb: str,
    caller_identity: str,
    caller_role: str,
    work_claim: str | None,
    target_ref: str | None,
    params_redacted: Mapping[str, Any],
    result: str,
    changed: bool,
    rate_limit_key: str | None,
    disabled_scope: str | None,
    disabled_reason_ref: str | None,
    broker_identity: str,
    evidence: Mapping[str, Any] | None = None,
    started_at: str,
    finished_at: str,
    event: str = "final",
) -> dict[str, Any]:
    record = {
        "schema": "ce.host_ops.audit.v1",
        "event": event,
        "request_id": request_id,
        "verb": verb,
        "caller_identity": caller_identity,
        "caller_role": caller_role,
        "work_claim": work_claim,
        "target_ref": target_ref,
        "params_redacted": dict(params_redacted),
        "result": result,
        "changed": bool(changed),
        "rate_limit_key": rate_limit_key,
        "disabled_scope": disabled_scope,
        "disabled_reason_ref": disabled_reason_ref,
        "started_at": started_at,
        "finished_at": finished_at,
        "broker_identity": broker_identity,
        "broker_version": "v1",
        "evidence": dict(evidence or {}),
    }
    assert_secret_free(record)
    return record
