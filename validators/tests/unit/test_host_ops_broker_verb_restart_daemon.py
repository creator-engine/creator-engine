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
from host_ops_broker.rate_limit import RateLimitRule

T0 = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


class RecordingSystemd:
    def __init__(self, *, active=True):
        self.calls = []
        self.active = active

    def get_state(self, unit):
        self.calls.append(("get_state", unit))
        state = "active" if self.active else "inactive"
        return {"active_state": state, "sub_state": "running" if self.active else "dead"}

    def restart(self, unit, mode):
        self.calls.append(("restart", unit, mode))
        self.active = True

    def wait_ready(self, unit, timeout_seconds):
        self.calls.append(("wait_ready", unit, timeout_seconds))
        return True


def _config(tmp_path, *, audit_path=None, overrides=None):
    return BrokerConfig(
        audit_log_path=str(audit_path or (tmp_path / "audit.jsonl")),
        kill_switch_path=str(tmp_path / "missing-kill.json"),
        broker_identity="host-ops-broker:test",
        unit_allowlist=frozenset({"ce-agent.service"}),
        daemon_map={"agent": "ce-agent.service"},
        rate_limit_overrides=overrides or {},
    )


def _request(params=None):
    return {
        "schema": "ce.host_ops.request.v1",
        "verb": "restart-daemon",
        "request_id": "hostops-restart",
        "caller": {"identity": "controller:dev", "role": "controller"},
        "params": params or {"daemon": "agent"},
        "reason": "repair",
        "created_at": "2026-07-08T12:00:00Z",
    }


def _records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def test_unknown_daemon_is_refused_before_adapter_call(tmp_path):
    adapter = RecordingSystemd()
    broker = HostOpsBroker(_config(tmp_path), systemd_adapter=adapter, now=lambda: T0)

    resp = broker.dispatch(_request({"daemon": "unknown"}))

    assert resp["result"] == "refused"
    assert adapter.calls == []


def test_valid_daemon_dispatches_to_adapter_with_correct_mode(tmp_path):
    adapter = RecordingSystemd()
    broker = HostOpsBroker(_config(tmp_path), systemd_adapter=adapter, now=lambda: T0)

    resp = broker.dispatch(_request({"daemon": "agent", "mode": "try-restart", "wait_ready_seconds": 7}))

    assert resp["result"] == "ok"
    assert ("restart", "ce-agent.service", "try-restart") in adapter.calls
    assert ("wait_ready", "ce-agent.service", 7) in adapter.calls


def test_wait_ready_seconds_outside_bound_is_refused(tmp_path):
    adapter = RecordingSystemd()
    broker = HostOpsBroker(_config(tmp_path), systemd_adapter=adapter, now=lambda: T0)

    resp = broker.dispatch(_request({"daemon": "agent", "wait_ready_seconds": 121}))

    assert resp["result"] == "refused"
    assert adapter.calls == []


def test_try_restart_inactive_returns_already_converged(tmp_path):
    adapter = RecordingSystemd(active=False)
    broker = HostOpsBroker(_config(tmp_path), systemd_adapter=adapter, now=lambda: T0)

    resp = broker.dispatch(_request({"daemon": "agent", "mode": "try-restart"}))

    assert resp["result"] == "already-converged"
    assert all(call[0] != "restart" for call in adapter.calls)


def test_audit_contains_restart_fields(tmp_path):
    adapter = RecordingSystemd()
    broker = HostOpsBroker(_config(tmp_path), systemd_adapter=adapter, now=lambda: T0)

    resp = broker.dispatch(_request({"daemon": "agent", "mode": "restart", "wait_ready_seconds": 30}))

    assert resp["result"] == "ok"
    final = _records(tmp_path / "audit.jsonl")[-1]
    assert final["evidence"]["daemon"] == "agent"
    assert final["evidence"]["unit"] == "ce-agent.service"
    assert final["evidence"]["mode"] == "restart"
    assert final["evidence"]["pre_state"]["active_state"] == "active"
    assert final["evidence"]["post_state"]["active_state"] == "active"
    assert final["evidence"]["wait_ready_seconds"] == 30
    assert final["evidence"]["changed"] is True
    assert final["evidence"]["result"] == "ok"


def test_restart_daemon_rate_limit_three_per_fifteen_minutes(tmp_path):
    adapter = RecordingSystemd()
    broker = HostOpsBroker(_config(tmp_path), systemd_adapter=adapter, now=lambda: T0)

    assert [broker.dispatch(_request())["result"] for _ in range(4)] == [
        "ok",
        "ok",
        "ok",
        "rate-limited",
    ]
    assert len([call for call in adapter.calls if call[0] == "restart"]) == 3


def test_pre_mutation_audit_fail_closed_before_adapter_call(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir")
    audit_path = blocker / "audit.jsonl"
    adapter = RecordingSystemd()
    broker = HostOpsBroker(_config(tmp_path, audit_path=audit_path), systemd_adapter=adapter, now=lambda: T0)

    resp = broker.dispatch(_request())

    assert resp["result"] == "failed"
    assert resp["details"]["error_class"] == "audit-pre-mutation"
    assert adapter.calls == []
