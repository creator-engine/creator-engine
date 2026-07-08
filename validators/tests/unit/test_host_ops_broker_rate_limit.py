from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOST_OPS_ROOT = ROOT / "tools" / "host-ops-broker"
if str(HOST_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(HOST_OPS_ROOT))

from host_ops_broker.broker import HostOpsBroker
from host_ops_broker.config import BrokerConfig
from host_ops_broker.rate_limit import DEFAULT_RATE_LIMITS, InMemoryRateLimiter, RateLimitRule

T0 = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)


class MutableClock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now


class CountingSystemd:
    def __init__(self):
        self.restarts = 0

    def get_state(self, unit):
        return {"active_state": "active", "sub_state": "running"}

    def restart(self, unit, mode):
        self.restarts += 1

    def wait_ready(self, unit, timeout_seconds):
        return True


def _config(tmp_path, *, overrides=None):
    return BrokerConfig(
        audit_log_path=str(tmp_path / "audit.jsonl"),
        kill_switch_path=str(tmp_path / "missing-kill.json"),
        broker_identity="host-ops-broker:test",
        unit_allowlist=frozenset({"ce-agent.service", "ce-other.service"}),
        daemon_map={"agent": "ce-agent.service", "other": "ce-other.service"},
        rate_limit_overrides=overrides or {},
    )


def _request(daemon="agent", caller="controller:dev"):
    return {
        "schema": "ce.host_ops.request.v1",
        "verb": "restart-daemon",
        "request_id": f"hostops-{daemon}-{caller}",
        "caller": {"identity": caller, "role": "controller"},
        "params": {"daemon": daemon},
        "reason": "repair",
        "created_at": "2026-07-08T12:00:00Z",
    }


def _records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def test_rate_limit_defaults_match_design_table():
    assert DEFAULT_RATE_LIMITS["status"] == RateLimitRule(30, 60)
    assert DEFAULT_RATE_LIMITS["restart-daemon"] == RateLimitRule(3, 15 * 60)
    assert DEFAULT_RATE_LIMITS["prepare-owned-state-root"] == RateLimitRule(6, 60 * 60)
    assert DEFAULT_RATE_LIMITS["rotate-attempt-log"] == RateLimitRule(6, 60 * 60)
    assert DEFAULT_RATE_LIMITS["repair-systemd-unit"] == RateLimitRule(3, 15 * 60)
    assert DEFAULT_RATE_LIMITS["run-ephemeral-container"] == RateLimitRule(3, 60 * 60)
    assert DEFAULT_RATE_LIMITS["prune-stopped-owned-containers"] == RateLimitRule(3, 60 * 60)
    assert DEFAULT_RATE_LIMITS["snapshot-openbao"] == RateLimitRule(2, 60 * 60)
    assert DEFAULT_RATE_LIMITS["restore-drill-openbao"] == RateLimitRule(1, 6 * 60 * 60)


def test_accepted_then_rate_limited_requests_and_no_host_mutation_on_limit(tmp_path):
    clock = MutableClock()
    adapter = CountingSystemd()
    broker = HostOpsBroker(
        _config(tmp_path, overrides={"restart-daemon": RateLimitRule(1, 900)}),
        systemd_adapter=adapter,
        now=clock,
    )

    assert broker.dispatch(_request())["result"] == "ok"
    assert broker.dispatch(_request())["result"] == "rate-limited"

    assert adapter.restarts == 1
    records = _records(tmp_path / "audit.jsonl")
    assert records[-1]["result"] == "rate-limited"


def test_refused_unknown_target_does_not_consume_rate_bucket(tmp_path):
    store = {}
    limiter = InMemoryRateLimiter(now=lambda: T0, store=store)
    broker = HostOpsBroker(_config(tmp_path), rate_limiter=limiter, now=lambda: T0)

    resp = broker.dispatch(_request(daemon="unknown"))

    assert resp["result"] == "refused"
    assert store == {}


def test_per_caller_per_target_bucket_isolation_and_clock_window(tmp_path):
    clock = MutableClock()
    broker = HostOpsBroker(
        _config(tmp_path, overrides={"restart-daemon": RateLimitRule(1, 60)}),
        now=clock,
    )

    assert broker.dispatch(_request(daemon="agent", caller="controller:a"))["result"] == "ok"
    assert broker.dispatch(_request(daemon="agent", caller="controller:a"))["result"] == "rate-limited"
    assert broker.dispatch(_request(daemon="other", caller="controller:a"))["result"] == "ok"
    assert broker.dispatch(_request(daemon="agent", caller="controller:b"))["result"] == "ok"
    clock.now = T0 + timedelta(seconds=61)
    assert broker.dispatch(_request(daemon="agent", caller="controller:a"))["result"] == "ok"
