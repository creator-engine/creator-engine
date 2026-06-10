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
from creator_engine_validator.runner.spend_gate import breach_record_body, fleet_spend_meter
from creator_engine_validator.runner.usage_tap import UsageTurn, fleet_token_rate
from creator_engine_validator.runtime_evidence_spine import append


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
