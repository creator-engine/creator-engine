"""Unit tests for the v3 G-6 coordination layer (the Scope dispatch spine). PURE."""

from __future__ import annotations

import pytest

from creator_engine_validator import coordination as co
from creator_engine_validator.runner import spend_gate as sg


def _scope(**overrides):
    base = {
        "kind": "scope-record", "record_type": "scope", "schema_version": "1",
        "scope_id": "demo-scope", "intent": "do the thing",
        "acceptance_criteria": ["it works"], "appetite": {"amount": 12.0, "unit": "$"},
        "mutation_class": "code",
        "ratification": {"approver_ref": "a" * 64, "ratified_scope_sha": "b" * 64},
        "state": "ready",
    }
    base.update(overrides)
    return base


# --- the canon skin (conserve the machine; derive the phase) -----------------
def test_phase_mapping_covers_the_conserved_lifecycle():
    assert set(co.PHASE_BY_STATE) == set(co.SPEC_LIFECYCLE)
    assert set(co.PHASE_BY_STATE.values()) <= set(co.COGNITIVE_PHASES)
    assert co.cognitive_phase("draft") == "Frame"
    assert co.cognitive_phase("ready") == "Shape"
    assert co.cognitive_phase("in_progress") == "Build"
    assert co.cognitive_phase("verified") == "Review"
    assert co.cognitive_phase("ratified") == "Ship"
    assert co.cognitive_phase("done") == "Ship"
    assert co.cognitive_phase(None) == "Frame"  # absent ⇒ draft ⇒ Frame


def test_board_label_mapping():
    assert co.board_label("draft") == "BACKLOG"
    assert co.board_label("ready") == "READY"
    assert co.board_label("done") == "MERGE"


# --- Definition-of-Ready front gate ------------------------------------------
def test_scope_is_ready_complete():
    ok, reasons = co.scope_is_ready(_scope())
    assert ok and reasons == []


@pytest.mark.parametrize("mutation,field", [
    ({"intent": ""}, "intent"),
    ({"acceptance_criteria": []}, "acceptance_criteria"),
    ({"appetite": {"amount": 0, "unit": "$"}}, "amount"),
    ({"appetite": {"amount": 5, "unit": "eur"}}, "unit"),
    ({"mutation_class": "bogus"}, "mutation_class"),
])
def test_scope_is_ready_teeth(mutation, field):
    ok, reasons = co.scope_is_ready(_scope(**mutation))
    assert not ok
    assert any(field in r for r in reasons)


def test_is_ratified():
    assert co.is_ratified(_scope())
    assert not co.is_ratified(_scope(ratification=None))
    assert not co.is_ratified(_scope(ratification={"approver_ref": "short", "ratified_scope_sha": "b" * 64}))


# --- the appetite → tokenomics-cap join (the explicit G-5 link) ---------------
def test_appetite_to_spend_envelope_run_scope_and_default_window():
    env = co.appetite_to_spend_envelope({"amount": 25.0, "unit": "$"})
    assert env == {"scope": "run", "amount": 25.0, "unit": "$", "window": "per_run"}


def test_appetite_to_spend_envelope_honors_window_and_percent_regime():
    env = co.appetite_to_spend_envelope({"amount": 80.0, "unit": "%", "window": "rolling_5h"})
    assert env == {"scope": "run", "amount": 80.0, "unit": "%", "window": "rolling_5h"}


@pytest.mark.parametrize("bad", [{"amount": 0, "unit": "$"}, {"amount": 5, "unit": "x"}, {"unit": "$"}, "nope"])
def test_appetite_to_spend_envelope_rejects_malformed(bad):
    with pytest.raises(ValueError):
        co.appetite_to_spend_envelope(bad)


def test_derived_envelope_is_admitted_by_the_g5_spend_gate_unchanged():
    env = co.appetite_to_spend_envelope({"amount": 10.0, "unit": "$"})
    # fresh ledger -> admitted; an exhausted run -> refused by the SAME G-5 gate.
    assert sg.admit([env], [], run_id="r1").verdict == "allowed"
    spent = [sg.meter_record_body(policy_sha="a" * 64, run_id="r1", recorded_at="t",
                                  amount=10.0, unit="$", window="per_run")]
    assert sg.admit([env], spent, run_id="r1").verdict == "denied"


# --- state-as-projection over the conserved lifecycle ------------------------
def test_project_scope_state_signal_cascade():
    s = _scope()
    assert co.project_scope_state(s, dor_ready=True, bet_placed=True)["state"] == "ready"
    assert co.project_scope_state(s, dispatched=True)["state"] == "in_progress"
    assert co.project_scope_state(s, reviewed=True)["state"] == "verified"
    assert co.project_scope_state(s, final_ratified=True)["state"] == "ratified"
    assert co.project_scope_state(s, merged=True)["state"] == "done"


def test_project_scope_state_ready_requires_both_dor_and_bet():
    s = _scope(ratification=None, acceptance_criteria=[])  # no bet, DoR incomplete
    proj = co.project_scope_state(s)
    assert proj == {"state": "draft", "phase": "Frame", "board": "BACKLOG"}


def test_project_scope_state_defaults_from_scope_signals_and_exposes_canon_skin():
    proj = co.project_scope_state(_scope())  # complete + ratified -> ready
    assert proj == {"state": "ready", "phase": "Shape", "board": "READY"}


# --- the dispatch-assembly seam (front gate; produces G-4/G-5 run inputs) -----
def test_assemble_dispatch_produces_run_inputs_with_merged_envelope():
    plan = co.assemble_dispatch(_scope(), {"policy_id": "p", "spend_envelopes": [
        {"scope": "global", "amount": 100.0, "unit": "$", "window": "total"}]})
    assert isinstance(plan, co.DispatchPlan)
    assert plan.scope_id == "demo-scope" and plan.mutation_class == "code"
    # additive: the global envelope is preserved, the appetite-derived run envelope appended.
    scopes = [e["scope"] for e in plan.runtime_policy["spend_envelopes"]]
    assert scopes == ["global", "run"]
    assert plan.scope_ratification["approver_ref"] == "a" * 64


def test_assemble_dispatch_refuses_not_ready():
    r = co.assemble_dispatch(_scope(acceptance_criteria=[]), {})
    assert isinstance(r, co.DispatchRefusal) and r.reason == "not_ready"


def test_assemble_dispatch_refuses_not_ratified():
    r = co.assemble_dispatch(_scope(ratification=None), {})
    assert isinstance(r, co.DispatchRefusal) and r.reason == "not_ratified"


def test_assemble_dispatch_does_not_mutate_inputs():
    policy = {"policy_id": "p"}
    co.assemble_dispatch(_scope(), policy)
    assert "spend_envelopes" not in policy  # the input policy is untouched
