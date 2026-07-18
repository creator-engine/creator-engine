"""Unit tests for the v3 G-5 pure spend gate (admission + circuit-breaker).

RED->GREEN against fakes: rates / meters / records are injected; no live I/O.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from creator_engine_validator import runtime_evidence_spine as spine
from creator_engine_validator.runner import spend_gate as sg
from creator_engine_validator.runner.audit_overlay import AgentActionEvent
from creator_engine_validator.runner.work_unit_cap import WorkUnitDecision

PSHA = "a" * 64

RATES = [
    {"model": "opus", "input_per_mtok": 5.0, "output_per_mtok": 25.0},
    {
        "model": "sonnet",
        "input_per_mtok": 3.0,
        "output_per_mtok": 15.0,
        "cache_read_per_mtok": 0.3,
        "cache_write_per_mtok": 3.75,
    },
]

ENV = [
    {"scope": "global", "amount": 100.0, "unit": "$", "window": "total"},
    {"scope": "fleet", "amount": 50.0, "unit": "$", "window": "total", "fleet_id": "f1"},
    {"scope": "run", "amount": 10.0, "unit": "$", "window": "total"},
]


def test_work_unit_cap_precedes_usd_spend_without_changing_usd_behavior():
    event = AgentActionEvent(op="read", fidelity="faithful", timing="pre")
    denied = sg.decide_with_spend(
        event,
        {"gate_mode": "full"},
        work_unit_decision=WorkUnitDecision(False, "work_unit_cap_exhausted", {}, persist=False),
    )
    assert denied.verdict == "denied"
    assert "work-unit cap precedence" in denied.reason


# --- cost metering: the two regimes (Fork C) ---------------------------------
def test_compute_cost_input_output_and_default_cache_read_ratio():
    # 1M input @ $5 + 1M output @ $25 + 1M cache-read @ 0.1x input ($0.5) = $30.5
    cost = sg.compute_cost(
        {"input_tokens": 1_000_000, "output_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000},
        "opus",
        RATES,
    )
    assert cost == Decimal("30.50")


def test_compute_cost_explicit_cache_rates_and_creation():
    cost = sg.compute_cost(
        {
            "input_tokens": 1_000_000,
            "output_tokens": 0,
            "cache_read_input_tokens": 1_000_000,
            "cache_creation_input_tokens": 1_000_000,
        },
        "sonnet",
        RATES,
    )
    # 3 (input) + 0.3 (cache-read) + 3.75 (cache-write) = 7.05
    assert cost == Decimal("7.05")


def test_compute_cost_cache_creation_defaults_to_input_rate():
    cost = sg.compute_cost({"cache_creation_input_tokens": 1_000_000}, "opus", RATES)
    assert cost == Decimal("5")  # default cache-write = input rate


def test_compute_cost_unknown_model_raises_never_silently_zero():
    with pytest.raises(sg.UnknownModelRate):
        sg.compute_cost({"input_tokens": 1}, "haiku", RATES)


def test_compute_cost_is_deterministic():
    usage = {"input_tokens": 123_456, "output_tokens": 654_321}
    assert sg.compute_cost(usage, "opus", RATES) == sg.compute_cost(usage, "opus", RATES)


def test_seat_usage_pct_subscription_regime():
    meter = {"rolling_5h": {"used": 40.0, "limit": 100.0}, "rolling_weekly": {"used": 7.0, "limit": 70.0}}
    assert sg.seat_usage_pct(meter, "rolling_5h") == Decimal("40")
    assert sg.seat_usage_pct(meter, "rolling_weekly") == Decimal("10")
    assert sg.seat_usage_pct(meter, "absent") == Decimal("0")
    assert sg.seat_usage_pct({"w": {"used": 1, "limit": 0}}, "w") == Decimal("0")


# --- projection: state-as-projection over the spine --------------------------
def _ledger(amount, *, run_id="r1", fleet_id="f1", unit="$", window="total"):
    return sg.meter_record_body(
        policy_sha=PSHA, run_id=run_id, recorded_at="t", amount=amount,
        unit=unit, fleet_id=fleet_id, window=window,
    )


def _ledger_at(amount, ts, *, run_id="r1", fleet_id="fleet-a", unit="$", window="total"):
    return sg.meter_record_body(
        policy_sha=PSHA,
        run_id=run_id,
        recorded_at=ts,
        amount=amount,
        unit=unit,
        fleet_id=fleet_id,
        window=window,
    )


def test_project_spend_scope_rollup_and_filters():
    records = [
        _ledger(3, run_id="r1", fleet_id="f1"),
        _ledger(4, run_id="r2", fleet_id="f1"),
        _ledger(5, run_id="r3", fleet_id="f2"),
        {"record_type": "runtime_agent_action", "amount": 999},  # ignored: not a ledger leaf
        _ledger(7, run_id="r1", fleet_id="f1", unit="%"),  # ignored for $ projection
    ]
    assert sg.project_spend(records, "run", run_id="r1", unit="$") == Decimal("3")
    assert sg.project_spend(records, "fleet", fleet_id="f1", unit="$") == Decimal("7")
    assert sg.project_spend(records, "global", unit="$") == Decimal("12")
    assert sg.project_spend(records, "run", run_id="r1", unit="%") == Decimal("7")


def test_project_spend_window_filter():
    records = [_ledger(3, window="total"), _ledger(4, window="rolling_5h")]
    assert sg.project_spend(records, "run", run_id="r1", window="rolling_5h") == Decimal("4")


# --- fleet spend meter: pure fleet $/hr projection --------------------------
def test_fleet_spend_meter_totals_match_project_spend_and_rates_by_span():
    records = [
        _ledger_at(3, "2026-06-08T00:00:00Z", run_id="r1"),
        _ledger_at(5, "2026-06-08T02:00:00Z", run_id="r2"),
        _ledger_at(11, "2026-06-08T01:00:00Z", run_id="other", fleet_id="fleet-b"),
    ]
    meter = sg.fleet_spend_meter(records, fleet_id="fleet-a", window="total")
    assert meter.fleet_id == "fleet-a"
    assert meter.unit == "$"
    assert meter.spend == sg.project_spend(records, "fleet", fleet_id="fleet-a", window="total")
    assert meter.spend == Decimal("8")
    assert meter.record_count == 2
    assert meter.run_count == 2
    assert meter.span_hours == Decimal("2")
    assert meter.spend_per_hour == Decimal("4")


def test_fleet_spend_meter_single_leaf_has_no_rate():
    meter = sg.fleet_spend_meter(
        [_ledger_at(3, "2026-06-08T00:00:00Z")],
        fleet_id="fleet-a",
    )
    assert meter.spend == Decimal("3")
    assert meter.record_count == 1
    assert meter.run_count == 1
    assert meter.span_hours is None
    assert meter.spend_per_hour is None


def test_fleet_spend_meter_empty_records_zero_none():
    meter = sg.fleet_spend_meter([], fleet_id="fleet-a")
    assert meter.spend == Decimal("0")
    assert meter.record_count == 0
    assert meter.run_count == 0
    assert meter.span_hours is None
    assert meter.spend_per_hour is None


def test_fleet_spend_meter_wall_clock_filter_narrows_total_and_rate():
    records = [
        _ledger_at(1, "2026-06-08T00:00:00Z", run_id="r0"),
        _ledger_at(3, "2026-06-08T01:00:00Z", run_id="r1"),
        _ledger_at(6, "2026-06-08T03:00:00Z", run_id="r2"),
    ]
    meter = sg.fleet_spend_meter(
        records,
        fleet_id="fleet-a",
        since="2026-06-08T00:30:00Z",
        until="2026-06-08T02:30:00Z",
    )
    assert meter.spend == Decimal("3")
    assert meter.record_count == 1
    assert meter.run_count == 1
    assert meter.span_hours == Decimal("2")
    assert meter.spend_per_hour == Decimal("1.5")


def test_fleet_spend_meter_window_passthrough_and_global_fold():
    records = [
        _ledger_at(2, "2026-06-08T00:00:00Z", run_id="r1", window=None),
        _ledger_at(3, "2026-06-08T01:00:00Z", run_id="r2", window="rolling_5h"),
        _ledger_at(5, "2026-06-08T02:00:00Z", run_id="r3", window="total"),
        _ledger_at(7, "2026-06-08T01:00:00Z", run_id="r4", fleet_id="fleet-b"),
    ]
    rolling = sg.fleet_spend_meter(records, fleet_id="fleet-a", window="rolling_5h")
    assert rolling.spend == Decimal("5")  # untagged leaves are included, matching project_spend.
    assert rolling.record_count == 2

    global_meter = sg.fleet_spend_meter(records, fleet_id=None)
    assert global_meter.spend == sg.project_spend(records, "global")
    assert global_meter.spend == Decimal("17")


def test_fleet_spend_meter_is_deterministic():
    records = [
        _ledger_at(1, "2026-06-08T00:00:00Z", run_id="r1"),
        _ledger_at(2, "2026-06-08T01:00:00Z", run_id="r2"),
    ]
    assert sg.fleet_spend_meter(records, fleet_id="fleet-a") == sg.fleet_spend_meter(
        records,
        fleet_id="fleet-a",
    )


# --- admission gate (Fork A) -------------------------------------------------
def test_admit_allows_when_all_envelopes_have_headroom():
    d = sg.admit(ENV, [_ledger(1)], run_id="r1", fleet_id="f1")
    assert d.verdict == "allowed" and d.signal == "ok"


def test_admit_refuses_exhausted_innermost_with_budget_exhausted_no_retry():
    records = [_ledger(10, run_id="r1", fleet_id="f1")]  # run cap = 10 -> exhausted
    d = sg.admit(ENV, records, run_id="r1", fleet_id="f1")
    assert d.verdict == "denied"
    assert d.signal == sg.SIGNAL_BUDGET_EXHAUSTED  # do NOT retry
    assert d.scope == "run"  # most-restrictive (innermost) reported


def test_admit_concurrency_throttle_vs_ok():
    assert sg.admit_concurrency(4, 4).signal == sg.SIGNAL_THROTTLE  # retry w/ backoff
    assert sg.admit_concurrency(1, 4).signal == sg.SIGNAL_OK
    assert sg.admit_concurrency(99, None).verdict == "allowed"  # no cap


# --- circuit-breaker (Fork A): synchronous soft/hard -------------------------
def test_meter_and_check_within_soft_hard_transitions_synchronously():
    chain = []
    body, d = sg.meter_and_check(ENV, chain, Decimal("6"), policy_sha=PSHA, run_id="r1",
                                 recorded_at="t1", fleet_id="f1", window="total")
    chain.append(spine.append(chain, body))
    assert d.tier == "" and d.verdict == "allowed"  # 6/10 = 0.6

    body, d = sg.meter_and_check(ENV, chain, Decimal("3"), policy_sha=PSHA, run_id="r1",
                                 recorded_at="t2", fleet_id="f1", window="total")
    chain.append(spine.append(chain, body))
    assert d.tier == "soft" and d.verdict == "allowed"  # 9/10 = 0.9 -> alert, continue

    body, d = sg.meter_and_check(ENV, chain, Decimal("2"), policy_sha=PSHA, run_id="r1",
                                 recorded_at="t3", fleet_id="f1", window="total")
    chain.append(spine.append(chain, body))
    assert d.tier == "hard" and d.verdict == "escalate"  # 11/10 -> pause+escalate
    assert d.signal == sg.SIGNAL_BUDGET_EXHAUSTED
    assert d.scope == "run"
    assert d.escalation_id and len(d.escalation_id) == 64


def test_breaker_escalation_id_is_value_free_no_dollar_amount():
    eid = sg.spend_escalation_id("r1", "run", "$", "hard")
    assert "$" not in eid and "10" not in eid  # opaque digest, no amounts
    assert eid == sg.spend_escalation_id("r1", "run", "$", "hard")  # deterministic


# --- spend records on the spine are tamper-evident ---------------------------
def test_spend_records_append_to_spine_and_verify_clean():
    chain = []
    for i, amt in enumerate([1, 2, 3]):
        body, _ = sg.meter_and_check(ENV, chain, Decimal(amt), policy_sha=PSHA, run_id="r1",
                                     recorded_at=f"t{i}", fleet_id="f1", window="total")
        chain.append(spine.append(chain, body))
    assert spine.verify_chain(chain) == []


def test_spend_record_tamper_is_detected():
    chain = []
    body, _ = sg.meter_and_check(ENV, chain, Decimal("1"), policy_sha=PSHA, run_id="r1",
                                 recorded_at="t0", fleet_id="f1", window="total")
    chain.append(spine.append(chain, body))
    chain[0] = dict(chain[0], amount=99999.0)  # mutate after hashing
    findings = spine.verify_chain(chain)
    assert any(f.kind == "content_address" for f in findings)


def test_breach_record_body_carries_two_signal_and_shape():
    body = sg.breach_record_body(
        policy_sha=PSHA, run_id="r1", recorded_at="t", breach_scope="run", breach_unit="$",
        tier="hard", signal=sg.SIGNAL_BUDGET_EXHAUSTED, limit=10, observed=11,
        decision_reason="hard", escalation_id="e" * 64,
    )
    assert body["kind"] == spine.RUNTIME_SPEND_BREACH_RECORD_KIND
    assert body["signal"] == "budget_exhausted" and body["tier"] == "hard"


# --- composition with the G-4 control point (precedence before the ladder) ---
def test_decide_with_spend_no_breach_delegates_to_action_gate():
    full = {"gate_mode_ladder": {"default_mode": "full"}}
    ev = AgentActionEvent(op="write", mutation_class="code", fidelity="faithful")
    assert sg.decide_with_spend(ev, full).verdict == "allowed"  # full allows


def test_decide_with_spend_hard_breach_overrides_even_full_mode():
    full = {"gate_mode_ladder": {"default_mode": "full"}}
    ev = AgentActionEvent(op="write", mutation_class="code", fidelity="faithful")
    hard = sg.SpendDecision(verdict="escalate", signal="budget_exhausted", reason="x",
                            scope="run", tier="hard", escalation_id="e" * 64)
    d = sg.decide_with_spend(ev, full, spend_decision=hard)
    assert d.verdict == "escalate"  # spend precedence survives full mode
    assert d.escalation_id == "e" * 64


def test_decide_with_spend_soft_breach_does_not_block():
    full = {"gate_mode_ladder": {"default_mode": "full"}}
    ev = AgentActionEvent(op="write", mutation_class="code", fidelity="faithful")
    soft = sg.SpendDecision(verdict="allowed", signal="ok", reason="x", scope="run", tier="soft")
    assert sg.decide_with_spend(ev, full, spend_decision=soft).verdict == "allowed"
