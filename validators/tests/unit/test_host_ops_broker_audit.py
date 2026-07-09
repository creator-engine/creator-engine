from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOST_OPS_ROOT = ROOT / "tools" / "host-ops-broker"
if str(HOST_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(HOST_OPS_ROOT))

from host_ops_broker.audit import AuditSecretLeak, append_audit, build_record, now_z

T0 = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


def _now():
    return T0


def _record(**overrides):
    raw = build_record(
        request_id="hostops-1",
        verb="status",
        caller_identity="controller:dev",
        caller_role="controller",
        work_claim=None,
        target_ref="status:global",
        params_redacted={"include": ["daemons"], "detail": "summary"},
        result="ok",
        changed=False,
        rate_limit_key="controller:dev:status:global",
        disabled_scope=None,
        disabled_reason_ref=None,
        broker_identity="host-ops-broker:test",
        evidence={"result": "ok"},
        started_at=now_z(_now),
        finished_at=now_z(_now),
    )
    raw.update(overrides)
    return raw


def test_append_creates_parent_and_jsonl_record(tmp_path):
    path = tmp_path / "nested" / "audit.jsonl"
    appended = append_audit(path, _record())
    assert path.is_file()
    assert appended["started_at"] == "2026-07-08T12:00:00Z"
    assert json.loads(path.read_text())["schema"] == "ce.host_ops.audit.v1"


def test_append_is_append_only_and_never_truncates(tmp_path):
    path = tmp_path / "audit.jsonl"
    append_audit(path, _record(request_id="hostops-1"))
    append_audit(path, _record(request_id="hostops-2"))
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["request_id"] == "hostops-1"
    assert json.loads(lines[1])["request_id"] == "hostops-2"


@pytest.mark.parametrize(
    "record",
    [
        {"token": "x"},
        {"nested": {"private_key": "x"}},
        {"note": "ghp_0123456789abcdef"},
        {"note": "github_pat_0123456789abcdef"},
        {"note": "eyJabc.def.ghi"},
    ],
)
def test_secret_by_key_or_token_shaped_value_is_rejected_before_write(tmp_path, record):
    path = tmp_path / "audit.jsonl"
    with pytest.raises(AuditSecretLeak):
        append_audit(path, record)
    assert not path.exists()


def test_params_redacted_contains_only_schema_safe_non_secret_fields(tmp_path):
    rec = _record(params_redacted={"daemon": "agent", "mode": "restart", "wait_ready_seconds": 30})
    append_audit(tmp_path / "audit.jsonl", rec)
    assert rec["params_redacted"] == {"daemon": "agent", "mode": "restart", "wait_ready_seconds": 30}


def test_started_and_finished_are_rfc3339_utc_z():
    rec = _record()
    assert rec["started_at"].endswith("Z")
    assert rec["finished_at"].endswith("Z")


def test_value_key_does_not_trigger_false_positive(tmp_path):
    """Keys containing 'value' as a substring must not trigger AuditSecretLeak."""
    path = tmp_path / "audit.jsonl"
    rec = _record(
        params_redacted={
            "default_value": "summary",
            "exit_value": 0,
            "return_value": "ok",
        }
    )
    append_audit(path, rec)
    assert path.is_file()
