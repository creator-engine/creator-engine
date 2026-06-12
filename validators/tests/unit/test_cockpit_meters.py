"""Unit tests for the unified resource/health meter projection (v3.5-B.4, L2).

The honesty-tier law: ONE meter strip unifying spend ($, MEASURED), token-rate
(MEASURED), context-window % (MEASURED, CONSUMED — never recomputed) and the
subscription-headroom slot (ESTIMATED — a labelled placeholder, NEVER a
number), plus soft/hard spend-breach banners. Meter math is NEVER re-implemented
in the Cockpit: every value must equal the shipped ``fleet_spend_meter`` /
``fleet_token_rate`` / ``context_meter`` / ``spend_meter_from_spine`` outputs
exactly. An absent source degrades to ``UNAVAILABLE`` — never a fabricated
number.
"""

from __future__ import annotations

import json

from creator_engine_validator import v3_session
from creator_engine_validator.runner import cockpit_demo_seed, cockpit_readmodel
from creator_engine_validator.runner.spend_gate import (
    breach_record_body,
    fleet_spend_meter,
    project_spend,
)
from creator_engine_validator.runner.usage_tap import UsageTurn, fleet_token_rate
from creator_engine_validator.runtime_evidence_spine import append, verify_chain


def _demo_snapshot() -> dict:
    return cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())


def _flat_records(seed: dict) -> list[dict]:
    return [record for chain in seed["chains"].values() for record in chain]


# --- no parallel math: every tile equals the shipped projection ---------------

def test_spend_tile_equals_fleet_spend_meter_exactly():
    seed = cockpit_demo_seed.seed()
    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **seed)
    expected = fleet_spend_meter(_flat_records(seed), unit="$")
    tile = snapshot["meters"]["spend"]
    assert tile["badge"] == "MEASURED"
    assert tile["unit"] == "$"
    assert tile["spend"] == float(expected.spend)
    assert tile["record_count"] == expected.record_count
    assert tile["run_count"] == expected.run_count
    assert tile["spend_per_hour"] == (
        float(expected.spend_per_hour) if expected.spend_per_hour is not None else None
    )


def test_token_rate_tile_equals_fleet_token_rate_exactly():
    seed = cockpit_demo_seed.seed()
    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **seed)
    turns = [
        UsageTurn(
            session_id=t["session_id"],
            model=t["model"],
            recorded_at=t["recorded_at"],
            usage=t["usage"],
        )
        for t in seed["usage_turns"]
    ]
    expected = fleet_token_rate(turns)
    tile = snapshot["meters"]["token_rate"]
    assert tile["badge"] == "MEASURED"
    assert tile["total_tokens"] == expected.total_tokens
    assert tile["turn_count"] == expected.turn_count
    assert tile["tokens_per_hour"] == (
        float(expected.tokens_per_hour) if expected.tokens_per_hour is not None else None
    )


def test_context_tile_consumes_the_harness_number_via_context_meter():
    seed = cockpit_demo_seed.seed()
    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **seed)
    expected = v3_session.context_meter(seed["context_pct"])
    tile = snapshot["meters"]["context"]
    assert tile["badge"] == "MEASURED"
    assert tile["pct"] == expected.pct
    assert tile["state"] == expected.state


# --- honesty badges -----------------------------------------------------------

def test_every_tile_carries_an_honesty_badge():
    snapshot = _demo_snapshot()
    meters = snapshot["meters"]
    for tile_name in ("spend", "token_rate", "context", "subscription_headroom"):
        assert meters[tile_name]["badge"] in ("MEASURED", "ESTIMATED", "UNAVAILABLE"), tile_name


def test_estimated_tile_is_a_labelled_placeholder_never_a_number():
    snapshot = _demo_snapshot()
    tile = snapshot["meters"]["subscription_headroom"]
    assert tile["badge"] == "ESTIMATED"
    assert tile["value"] is None
    assert "estimator not yet shipped" in tile["placeholder"]


def test_absent_sources_degrade_to_unavailable_never_fabricate():
    snapshot = cockpit_readmodel.fold_snapshot()
    meters = snapshot["meters"]
    assert meters["spend"]["badge"] == "UNAVAILABLE"
    assert meters["spend"]["spend"] is None
    assert meters["token_rate"]["badge"] == "UNAVAILABLE"
    assert meters["token_rate"]["tokens_per_hour"] is None
    assert meters["context"]["badge"] == "UNAVAILABLE"
    assert meters["context"]["pct"] is None
    # The placeholder slot stays an ESTIMATED label even with nothing else.
    assert meters["subscription_headroom"]["badge"] == "ESTIMATED"
    assert meters["banners"] == []


# --- breach banners (soft amber vs hard gate-red) ------------------------------

def _breach_chain(tier: str, signal: str, minute: int) -> list[dict]:
    chain: list[dict] = []
    body = breach_record_body(
        policy_sha=cockpit_demo_seed.DEMO_POLICY_SHA,
        run_id=f"run-{tier}",
        recorded_at=f"2026-07-01T09:{minute:02d}:00Z",
        breach_scope="run",
        breach_unit="$",
        tier=tier,
        signal=signal,
        limit=10,
        observed=8 if tier == "soft" else 10,
        decision_reason=f"{tier} breach fixture",
    )
    chain.append(append(chain, body))
    return chain


def test_soft_vs_hard_banner_mapping():
    snapshot = cockpit_readmodel.fold_snapshot(
        chains={
            "run-soft": _breach_chain("soft", "throttle", 5),
            "run-hard": _breach_chain("hard", "budget_exhausted", 9),
        }
    )
    banners = snapshot["meters"]["banners"]
    assert len(banners) == 2
    by_tier = {b["tier"]: b for b in banners}
    assert by_tier["soft"]["action"] == "alert + continue"
    assert by_tier["hard"]["action"] == "pause + escalate"
    assert by_tier["soft"]["signal"] == "throttle"
    assert by_tier["hard"]["signal"] == "budget_exhausted"
    # Newest first.
    assert banners[0]["tier"] == "hard"


def test_demo_hard_breach_banner_renders_with_run_meter_state():
    seed = cockpit_demo_seed.seed()
    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **seed)
    banners = snapshot["meters"]["banners"]
    hard = [b for b in banners if b["tier"] == "hard"]
    assert hard, "the demo must carry the hard-breach banner"
    banner = hard[0]
    assert banner["run_id"] == "spend-hard-breach"
    # The per-run breaker state reuses the REAL G-5 projection via v3_session.
    expected = v3_session.spend_meter_from_spine(
        _flat_records(seed), banner["limit"], run_id=banner["run_id"]
    )
    assert banner["run_meter"]["state"] == expected.state
    assert banner["run_meter"]["spent"] == (
        float(expected.spent) if expected.spent is not None else None
    )


# --- JSON parity ---------------------------------------------------------------

def test_meters_json_round_trip():
    snapshot = _demo_snapshot()
    assert json.loads(json.dumps(snapshot, sort_keys=True)) == snapshot
    assert "meters" in snapshot


# --- v3.1-B.7: the fleet COST meter (per-scope $ + UNPRICED honesty tiers) -----

def _ledger(run_id: str, amount: float, model: str = "claude-opus-4-8") -> dict:
    return {
        "record_type": "runtime_spend_ledger",
        "run_id": run_id,
        "unit": "$",
        "amount": amount,
        "model": model,
    }


def _act(run_id: str) -> dict:
    return {"record_type": "runtime_agent_action", "run_id": run_id, "op": "write"}


def _outcome(run_id: str) -> dict:
    return {"record_type": "runtime_run_outcome", "run_id": run_id, "outcome": "pr_opened"}


def _mixed_chains() -> dict:
    return {
        "measured-run": [_ledger("measured-run", 2.0), _ledger("measured-run", 1.0, "claude-fable-5")],
        "unpriced-run": [_act("unpriced-run"), _act("unpriced-run")],
        "outcome-only": [_outcome("outcome-only")],
        "empty-run": [],
    }


def test_fold_cost_meter_per_scope_spend_reuses_project_spend():
    chains = _mixed_chains()
    cost = cockpit_readmodel.fold_cost_meter(chains)
    rows = {r["scope_id"]: r for r in cost["scopes"]}
    measured = rows["measured-run"]
    assert measured["tier"] == "MEASURED"
    # No parallel math: the per-scope $ equals project_spend EXACTLY.
    assert measured["spend"] == float(
        project_spend(chains["measured-run"], "run", run_id="measured-run", unit="$")
    )
    assert measured["spend"] == 3.0
    assert measured["leaf_count"] == 2
    assert measured["models"] == ["claude-fable-5", "claude-opus-4-8"]
    assert "unpriced_turns" not in measured


def test_fold_cost_meter_tier_classification():
    cost = cockpit_readmodel.fold_cost_meter(_mixed_chains())
    rows = {r["scope_id"]: r for r in cost["scopes"]}
    assert rows["measured-run"]["tier"] == "MEASURED"
    # UNPRICED with actions only — and NEVER a $ figure (no silent $0 lie).
    assert rows["unpriced-run"]["tier"] == "UNPRICED"
    assert rows["unpriced-run"]["spend"] is None
    assert rows["unpriced-run"]["unpriced_turns"] == 2
    assert rows["unpriced-run"]["leaf_count"] == 0
    # UNPRICED via a terminal outcome with zero actions -> zero turns.
    assert rows["outcome-only"]["tier"] == "UNPRICED"
    assert rows["outcome-only"]["unpriced_turns"] == 0
    # UNAVAILABLE on an empty chain.
    assert rows["empty-run"]["tier"] == "UNAVAILABLE"
    assert rows["empty-run"]["spend"] is None


def test_fold_cost_meter_fleet_rollup_reuses_fleet_spend_meter():
    chains = _mixed_chains()
    cost = cockpit_readmodel.fold_cost_meter(chains)
    fleet = cost["fleet"]
    flat = [r for c in chains.values() for r in c]
    expected = fleet_spend_meter(flat, unit="$")
    assert fleet["measured_spend"] == float(expected.spend) == 3.0
    assert fleet["measured_run_count"] == 1
    assert fleet["unpriced_run_count"] == 2
    assert fleet["total_run_count"] == 4
    assert fleet["badge"] == "MEASURED"
    assert cost["badge"] == "MEASURED"
    # The headroom heart: the measured $ is declared a FLOOR, not the whole cost.
    assert "FLOOR" in cost["headroom_note"]
    assert "2 of 4 runs are unpriced" in cost["headroom_note"]


def test_fold_cost_meter_none_chains_is_unavailable():
    cost = cockpit_readmodel.fold_cost_meter(None)
    assert cost["badge"] == "UNAVAILABLE"
    assert cost["scopes"] == []
    assert cost["fleet"]["measured_spend"] is None
    assert cost["fleet"]["badge"] == "UNAVAILABLE"
    assert cost["headroom_note"] is None


def test_fold_cost_meter_is_pure_and_json_serializable():
    chains = _mixed_chains()
    first = cockpit_readmodel.fold_cost_meter(chains)
    second = cockpit_readmodel.fold_cost_meter(chains)
    # Deterministic (no hidden state / clock / rng) and input-preserving.
    assert first == second
    assert json.loads(json.dumps(first, sort_keys=True)) == first
    assert chains == _mixed_chains()


def test_cost_section_is_wired_into_meters():
    snapshot = cockpit_readmodel.fold_snapshot(chains=_mixed_chains())
    assert "cost" in snapshot["meters"]
    assert snapshot["meters"]["cost"]["fleet"]["measured_spend"] == 3.0


def test_cost_meter_unavailable_when_chains_absent():
    snapshot = cockpit_readmodel.fold_snapshot()
    assert snapshot["meters"]["cost"]["badge"] == "UNAVAILABLE"


def test_demo_cost_meter_shows_both_tiers_and_chains_verify():
    seed = cockpit_demo_seed.seed()
    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **seed)
    cost = snapshot["meters"]["cost"]
    # The existing MEASURED pair sums to $13.30 (gate-uploads $3.30 + breach $10).
    assert cost["fleet"]["measured_spend"] == 13.30
    measured = [r for r in cost["scopes"] if r["tier"] == "MEASURED"]
    unpriced = [r for r in cost["scopes"] if r["tier"] == "UNPRICED"]
    assert len(measured) >= 2
    # The EXPLICIT subscription (unpriced) run is on the board, both tiers shown.
    assert any(r["scope_id"] == "subscription-seat" for r in unpriced)
    # NEVER a $0 lie: an unpriced run carries no $ figure.
    for row in unpriced:
        assert row["spend"] is None
    # The seed's tamper-evidence is REAL — every seed chain verifies clean.
    for run_id, chain in seed["chains"].items():
        assert verify_chain(chain) == [], f"seed chain {run_id!r} must verify clean"
