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


class RecordingStatus:
    def __init__(self, fail=()):
        self.calls = []
        self.fail = set(fail)

    def _check(self, name, *, target, detail):
        self.calls.append((name, target, detail))
        if name in self.fail:
            raise RuntimeError(name)
        return {"state": "ok", "name": name}

    def check_daemons(self, *, target, detail):
        return self._check("daemons", target=target, detail=detail)

    def check_systemd(self, *, target, detail):
        return self._check("systemd", target=target, detail=detail)

    def check_containers(self, *, target, detail):
        return self._check("containers", target=target, detail=detail)

    def check_state_roots(self, *, target, detail):
        return self._check("state_roots", target=target, detail=detail)

    def check_openbao(self, *, target, detail):
        return self._check("openbao", target=target, detail=detail)


def _config(tmp_path, overrides=None):
    return BrokerConfig(
        audit_log_path=str(tmp_path / "audit.jsonl"),
        kill_switch_path=str(tmp_path / "missing-kill.json"),
        broker_identity="host-ops-broker:test",
        unit_allowlist=frozenset({"ce-agent.service"}),
        daemon_map={"agent": "ce-agent.service"},
        container_namespaces=frozenset({"ce"}),
        state_roots={"controller": "/var/lib/ce/controller"},
        backup_profiles=frozenset({"daily"}),
        rate_limit_overrides=overrides or {},
    )


def _request(params=None):
    return {
        "schema": "ce.host_ops.request.v1",
        "verb": "status",
        "request_id": "hostops-status",
        "caller": {"identity": "controller:dev", "role": "controller"},
        "params": params or {},
        "created_at": "2026-07-08T12:00:00Z",
    }


def _last_record(path):
    return json.loads(Path(path).read_text().splitlines()[-1])


def test_status_include_target_and_detail_are_honored(tmp_path):
    adapter = RecordingStatus()
    broker = HostOpsBroker(_config(tmp_path), status_adapter=adapter, now=lambda: T0)

    resp = broker.dispatch(_request({"include": ["daemons", "systemd"], "target": "agent", "detail": "diagnostic"}))

    assert resp["result"] == "ok"
    assert adapter.calls == [("daemons", "agent", "diagnostic"), ("systemd", "agent", "diagnostic")]
    assert resp["details"]["detail"] == "diagnostic"


def test_status_unknown_target_is_refused_before_adapter(tmp_path):
    adapter = RecordingStatus()
    broker = HostOpsBroker(_config(tmp_path), status_adapter=adapter, now=lambda: T0)

    resp = broker.dispatch(_request({"target": "not-ce"}))

    assert resp["result"] == "refused"
    assert adapter.calls == []


def test_status_returns_degraded_with_failed_classes(tmp_path):
    adapter = RecordingStatus(fail={"containers", "openbao"})
    broker = HostOpsBroker(_config(tmp_path), status_adapter=adapter, now=lambda: T0)

    resp = broker.dispatch(_request({"include": ["containers", "openbao"]}))

    assert resp["result"] == "degraded"
    assert resp["details"]["degraded_checks"] == ["containers", "openbao"]


def test_status_is_read_only_and_audit_contains_required_fields(tmp_path):
    adapter = RecordingStatus()
    broker = HostOpsBroker(_config(tmp_path), status_adapter=adapter, now=lambda: T0)

    resp = broker.dispatch(_request({"include": ["daemons"], "detail": "summary"}))

    assert resp["changed"] is False
    rec = _last_record(tmp_path / "audit.jsonl")
    assert rec["params_redacted"]["include"] == ["daemons"]
    assert rec["params_redacted"]["detail"] == "summary"
    assert rec["evidence"]["health_summary"]["daemons"]["state"] == "ok"
    assert rec["evidence"]["degraded_checks"] == []
    assert rec["evidence"]["result"] == "ok"


def test_status_rate_limit_is_honored(tmp_path):
    broker = HostOpsBroker(
        _config(tmp_path, overrides={"status": RateLimitRule(1, 60)}),
        status_adapter=RecordingStatus(),
        now=lambda: T0,
    )

    assert broker.dispatch(_request())["result"] == "ok"
    assert broker.dispatch(_request())["result"] == "rate-limited"
