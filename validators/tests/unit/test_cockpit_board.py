"""Unit tests for the ops board + seat-detail projections (v3.5-B.2, L2).

The full fleet board: enriched cards (seat join, status/role chips, envelope
badge, headroom slot, terminal-outcome chip, inline blocked-why) with the
crabfleet all/mine/live filters — and the seat-detail sub-tabs (Stream with
Temporal-style event-groups + retry badges, Diffs, Evidence trail with a
TRUTHFUL ``verify_chain`` badge, Waterfall stage durations, Outcome) — ALL
folded in L2 and present in the ``--json`` snapshot (principle 6).
"""

from __future__ import annotations

import json

from creator_engine_validator import coordination
from creator_engine_validator.runner import cockpit_demo_seed, cockpit_readmodel


def _demo_snapshot(**overrides) -> dict:
    seed = cockpit_demo_seed.seed()
    seed.update(overrides)
    return cockpit_readmodel.fold_snapshot(demo=True, **seed)


def _card(snapshot: dict, scope_id: str) -> dict:
    cards = {c["scope_id"]: c for c in snapshot["board"]["cards"]}
    return cards[scope_id]


# --- the board: columns, joins, chips ----------------------------------------

def test_columns_still_derive_via_phase_by_state_only():
    snapshot = _demo_snapshot()
    assert snapshot["board"]["columns"] == list(coordination.COGNITIVE_PHASES)
    for card in snapshot["board"]["cards"]:
        assert card["phase"] == coordination.PHASE_BY_STATE[card["state"]]
    phases = {c["phase"] for c in snapshot["board"]["cards"]}
    assert phases == set(coordination.COGNITIVE_PHASES)


def test_cards_join_their_seats_by_the_documented_lane_rule():
    snapshot = _demo_snapshot()
    card = _card(snapshot, "gate-push-refusal")
    assert card["seat"]["controller_id"] == "ce-demo-builder-b"
    assert card["seat"]["role"] == "implementer"
    assert card["status_chip"] == "blocked"
    assert card["role_badge"] == "implementer"
    # A scope with no matching lane renders an unseated card, never a guess.
    unseated = _card(snapshot, "scope-billing-frame")
    assert unseated["seat"]["controller_id"] == "ce-demo-framer"


def test_card_carries_harness_and_model_provenance():
    snapshot = _demo_snapshot()
    spender = _card(snapshot, "spend-hard-breach")
    # model = the newest spend-ledger leaf on the seat's chain (real data).
    assert spender["seat"]["model"] == "claude-opus-4-8"
    assert spender["seat"]["harness"] == "claude"
    uploads = _card(snapshot, "gate-uploads")
    assert uploads["seat"]["model"] == "claude-fable-5"


def test_envelope_badge_and_headroom_slot():
    snapshot = _demo_snapshot()
    reviewer = _card(snapshot, "pr-300-review")
    assert reviewer["envelope_badge"] == "granted:pr_review"
    push = _card(snapshot, "gate-push-refusal")
    assert push["envelope_badge"] == "none"
    plain = _card(snapshot, "gate-uploads")
    assert plain["envelope_badge"] is None
    # The headroom sparkline SLOT exists and is honest (estimator unshipped).
    assert reviewer["headroom_slot"]["badge"] == "UNAVAILABLE"
    assert reviewer["headroom_slot"]["points"] == []


def test_terminal_outcome_chip_from_the_run_chain():
    snapshot = _demo_snapshot()
    assert _card(snapshot, "ship-pr-294")["outcome_chip"] == "pr_merged"
    assert _card(snapshot, "pr-300-review")["outcome_chip"] == "review_submitted"
    assert _card(snapshot, "gate-uploads")["outcome_chip"] is None


# --- blocked cards surface WHY inline ------------------------------------------

def test_blocked_card_names_its_refusal_inline():
    snapshot = _demo_snapshot()
    card = _card(snapshot, "gate-push-refusal")
    assert card["blocked"] is True
    assert card["blocked_source"] == "refusal-chain"
    assert "G2.007.2" in card["blocked_reason"]


def test_blocked_card_names_its_spend_breach_inline():
    snapshot = _demo_snapshot()
    card = _card(snapshot, "spend-hard-breach")
    assert card["blocked"] is True
    assert card["blocked_source"] == "spend-breach"
    assert "hard breach" in card["blocked_reason"]


def test_unblocked_cards_carry_no_blocked_reason():
    snapshot = _demo_snapshot()
    card = _card(snapshot, "gate-uploads")
    assert card["blocked"] is False
    assert card["blocked_reason"] is None


# --- the all/mine/live filters fold in L2 --------------------------------------

def test_filters_fold_in_l2():
    snapshot = _demo_snapshot(controller_id="ce-demo-builder-b")
    filters = snapshot["board"]["filters"]
    all_ids = {c["scope_id"] for c in snapshot["board"]["cards"]}
    assert set(filters["all"]) == all_ids
    assert filters["mine"] == ["gate-push-refusal"]
    # live = seats not closed/aborted; the shipped seat is closed.
    assert "ship-pr-294" not in filters["live"]
    assert "gate-push-refusal" in filters["live"]


def test_mine_filter_is_empty_when_no_identity_is_given():
    snapshot = _demo_snapshot()
    assert snapshot["board"]["filters"]["mine"] == []


# --- seat detail: Stream (event groups + retry), Diffs, Evidence, Waterfall, Outcome

def test_stream_collapses_event_groups_with_retry_badge():
    snapshot = _demo_snapshot()
    stream = snapshot["seat_detail"]["gate-push-refusal"]["stream"]
    groups = stream["groups"]
    denied = [g for g in groups if g.get("classification") == "denied"]
    assert denied, "the denied push span must appear"
    push_group = denied[0]
    assert push_group["count"] == 2  # two consecutive push attempts collapse
    assert push_group["retry"] is True
    assert push_group["color"] == "gate"
    allowed = [g for g in groups if g.get("classification") == "allowed"]
    assert allowed and allowed[0]["retry"] is False
    assert allowed[0]["color"] == "spark"


def test_diffs_summarize_write_targets():
    snapshot = _demo_snapshot()
    diffs = snapshot["seat_detail"]["gate-uploads"]["diffs"]
    paths = {f["path"]: f["writes"] for f in diffs["files"]}
    assert "src/uploads/gate.py" in paths
    assert paths["src/uploads/gate.py"] == 2


def test_evidence_trail_badge_is_truthful_on_a_tampered_chain():
    seed = cockpit_demo_seed.seed()
    chain = [dict(r) for r in seed["chains"]["gate-push-refusal"]]
    chain[-1]["target"] = "tampered-after-sealing"  # mutate WITHOUT re-hashing
    seed["chains"] = {**seed["chains"], "gate-push-refusal": chain}
    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **seed)
    evidence = snapshot["seat_detail"]["gate-push-refusal"]["evidence"]
    assert evidence["verified"] is False
    assert evidence["badge"] == "findings"
    # And the clean seed shows a clean badge.
    clean = _demo_snapshot()["seat_detail"]["gate-push-refusal"]["evidence"]
    assert clean["verified"] is True
    assert clean["badge"] == "clean"


def test_waterfall_durations_sum_from_lifecycle_records():
    snapshot = _demo_snapshot()
    waterfall = snapshot["seat_detail"]["ship-pr-294"]["waterfall"]
    stages = {s["stage"]: s["duration_seconds"] for s in waterfall["stages"]}
    # Seeded lifecycle stamps: provision 09:02 -> run 09:05 -> collect 09:14
    # -> teardown 09:16.
    assert stages["provision"] == 180.0
    assert stages["run"] == 540.0
    assert stages["collect"] == 120.0


def test_outcome_tab_carries_disposition_and_ratification():
    snapshot = _demo_snapshot()
    outcome = snapshot["seat_detail"]["ship-pr-294"]["outcome"]
    assert outcome["outcome"] == "pr_merged"
    assert outcome["change_set"]["pr_number"] == 294
    ratification = outcome["ratification"]
    assert ratification is not None
    assert len(ratification["ratified_prompt_sha"]) == 64
    assert len(ratification["approver_ref"]) == 64


def test_seat_detail_exists_for_every_seated_lane():
    snapshot = _demo_snapshot()
    lanes = {s["lane_id"] for s in snapshot["seats"]}
    assert set(snapshot["seat_detail"].keys()) == lanes
    for detail in snapshot["seat_detail"].values():
        for tab in ("stream", "diffs", "evidence", "waterfall", "outcome"):
            assert tab in detail, tab


# --- --json parity --------------------------------------------------------------

def test_board_and_seat_detail_json_round_trip():
    snapshot = _demo_snapshot()
    assert json.loads(json.dumps(snapshot, sort_keys=True)) == snapshot
    assert "seat_detail" in snapshot
    assert "filters" in snapshot["board"]
