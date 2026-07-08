from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOST_OPS_ROOT = ROOT / "tools" / "host-ops-broker"
if str(HOST_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(HOST_OPS_ROOT))

from host_ops_broker.broker import HostOpsBroker
from host_ops_broker.config import BrokerConfig
from host_ops_broker.rate_limit import InMemoryRateLimiter

T0 = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


def _now():
    return T0


def _config(tmp_path, kill_path):
    return BrokerConfig(
        audit_log_path=str(tmp_path / "audit.jsonl"),
        kill_switch_path=str(kill_path),
        broker_identity="host-ops-broker:test",
        unit_allowlist=frozenset({"ce-agent.service"}),
        daemon_map={"agent": "ce-agent.service"},
    )


def _request(verb="status", params=None, reason=None):
    raw = {
        "schema": "ce.host_ops.request.v1",
        "verb": verb,
        "request_id": f"hostops-{verb}",
        "caller": {"identity": "controller:dev", "role": "controller"},
        "params": params or {},
        "created_at": "2026-07-08T12:00:00Z",
    }
    if reason is not None:
        raw["reason"] = reason
    return raw


def _audit_records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def test_broker_wide_kill_switch_disables_status_and_mutating_verbs(tmp_path):
    kill = tmp_path / "kill.json"
    kill.write_text(json.dumps({"disabled": True, "reason_ref": "ops-stop"}))
    broker = HostOpsBroker(_config(tmp_path, kill), now=_now)

    status = broker.dispatch(_request())
    restart = broker.dispatch(_request("restart-daemon", {"daemon": "agent"}, "repair"))

    assert status["result"] == "disabled"
    assert restart["result"] == "disabled"
    records = _audit_records(tmp_path / "audit.jsonl")
    assert all(rec["result"] == "disabled" for rec in records)
    assert all(rec["disabled_scope"] == "broker" for rec in records)
    assert all(rec["disabled_reason_ref"] == "ops-stop" for rec in records)


def test_per_verb_disable_leaves_other_verbs_available(tmp_path):
    kill = tmp_path / "kill.json"
    kill.write_text(json.dumps({"disabled_verbs": {"restart-daemon": "daemon-freeze"}}))
    broker = HostOpsBroker(_config(tmp_path, kill), now=_now)

    assert broker.dispatch(_request())["result"] == "ok"
    restart = broker.dispatch(_request("restart-daemon", {"daemon": "agent"}, "repair"))
    assert restart["result"] == "disabled"
    last = _audit_records(tmp_path / "audit.jsonl")[-1]
    assert last["disabled_scope"] == "verb:restart-daemon"
    assert last["disabled_reason_ref"] == "daemon-freeze"


def test_unreadable_flag_file_fails_closed_as_broker_wide_disabled(tmp_path):
    kill = tmp_path / "kill-dir"
    kill.mkdir()
    broker = HostOpsBroker(_config(tmp_path, kill), now=_now)

    resp = broker.dispatch(_request())

    assert resp["result"] == "disabled"
    rec = _audit_records(tmp_path / "audit.jsonl")[0]
    assert rec["disabled_scope"] == "broker"
    assert rec["disabled_reason_ref"].startswith("kill-switch-read-error:")


def test_kill_switch_precedes_rate_limit_accounting(tmp_path):
    kill = tmp_path / "kill.json"
    kill.write_text(json.dumps({"disabled": True, "reason_ref": "ops-stop"}))
    store = {}
    limiter = InMemoryRateLimiter(now=_now, store=store)
    broker = HostOpsBroker(_config(tmp_path, kill), rate_limiter=limiter, now=_now)

    broker.dispatch(_request())

    assert store == {}
