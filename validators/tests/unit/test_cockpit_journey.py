"""Unit tests for the ce-ops#45 CEO-mode JOURNEY projection (L2, the pure fold).

The minimum journey surface (gate spec §1): a one-screen Frame→Shape→Build→
Review→Ship arc, an honest "where am I now" marker, a plain-language
"what needs me" feed translated 1:1 from the open AWAITING-OPERATOR queue, and a
deterministic non-engineer detail record per item — ALL computed in L2 and
present in ``snapshot["journey"]`` (no Textual import, the future-GUI seam).

These tests seed the PURE fold directly with dict fixtures (no I/O):
``cockpit_readmodel.fold_snapshot(scopes=[...], escalations=[...])``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from creator_engine_validator import coordination
from creator_engine_validator.runner import cockpit_readmodel

VALIDATORS_DIR = Path(__file__).resolve().parents[2]


def _scope(scope_id: str, *, intent: str = "do a thing") -> dict:
    """A DoR-valid scope fixture (so its derivable state is at least Ready)."""
    return {
        "kind": "scope-record",
        "scope_id": scope_id,
        "intent": intent,
        "acceptance_criteria": ["it works"],
        "appetite": {"amount": 5, "unit": "$"},
        "mutation_class": "code",
    }


def _escalation(esc_id: str, *, title: str, created_at: str, **extra) -> dict:
    rec = {
        "kind": "escalation-record",
        "record_type": "escalation",
        "schema_version": "1",
        "escalation_id": esc_id,
        "title": title,
        "decision_needed": extra.get("decision_needed", "decide something"),
        "recommendation": extra.get("recommendation", "do the safe thing"),
        "created_at": created_at,
    }
    if "source_ref" in extra:
        rec["source_ref"] = extra["source_ref"]
    if "resolved_at" in extra:
        rec["resolved_at"] = extra["resolved_at"]
    return rec


def _fold(**kwargs) -> dict:
    return cockpit_readmodel.fold_snapshot(**kwargs)


# --- 1. journey-json-section-present (no Textual import) ----------------------

def test_journey_json_section_present_without_textual():
    snapshot = _fold(scopes=[_scope("s-1")], escalations=[])
    assert "journey" in snapshot
    journey = snapshot["journey"]
    for key in ("arc", "now", "scopes", "needs_attention", "need_details", "counters"):
        assert key in journey, key
    # JSON-round-trippable (the future-GUI seam is real).
    assert json.loads(json.dumps(journey)) == journey


def test_journey_section_via_subprocess_imports_no_textual():
    code = (
        "import sys\n"
        "from creator_engine_validator.runner import cockpit_readmodel\n"
        "snap = cockpit_readmodel.fold_snapshot(scopes=[], escalations=[])\n"
        "assert 'journey' in snap\n"
        "assert 'textual' not in sys.modules, 'L2 journey must not import textual'\n"
        "assert 'watchfiles' not in sys.modules\n"
    )
    env = {**os.environ, "PYTHONPATH": str(VALIDATORS_DIR)}
    proc = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


# --- 2. journey-arc-is-canon -------------------------------------------------

def test_journey_arc_is_canon():
    snapshot = _fold(scopes=[_scope("s-1")], escalations=[])
    assert snapshot["journey"]["arc"]["stages"] == list(coordination.COGNITIVE_PHASES)


# --- 3. journey-stage-derives-from-scope-state -------------------------------

def test_journey_stage_derives_from_scope_state():
    scopes = [_scope("s-ready"), _scope("s-draft", intent="")]
    # s-draft has no intent -> not DoR-ready -> draft -> Frame.
    snapshot = _fold(scopes=scopes, escalations=[])
    cards = {c["scope_id"]: c for c in snapshot["board"]["cards"]}
    for jscope in snapshot["journey"]["scopes"]:
        card = cards[jscope["scope_id"]]
        # journey stage == board card phase == PHASE_BY_STATE[state]
        assert jscope["stage"] == card["phase"]
        assert jscope["stage"] == coordination.PHASE_BY_STATE[jscope["state"]]


def test_journey_stage_counts_sum_to_scope_count():
    scopes = [_scope(f"s-{i}") for i in range(4)]
    journey = _fold(scopes=scopes, escalations=[])["journey"]
    counts = journey["counters"]
    assert sum(counts["journey_stage_counts"].values()) == counts["journey_scope_count"]
    assert counts["journey_scope_count"] == 4


def test_journey_never_invents_a_third_vocabulary():
    journey = _fold(scopes=[_scope("s-1")], escalations=[])["journey"]
    forbidden = {"Planning", "Doing", "QA", "Done"}
    for stage in journey["arc"]["stages"]:
        assert stage not in forbidden
    for jscope in journey["scopes"]:
        assert jscope["stage"] in coordination.COGNITIVE_PHASES


# --- 4. journey-now-is-honest (multi-active -> basis-aware) -------------------

def test_journey_now_prefers_oldest_open_need():
    scopes = [_scope("s-1")]
    escs = [
        _escalation("aaaaaaaaaaaa", title="newer thing", created_at="2026-06-02T00:00:00Z"),
        _escalation("bbbbbbbbbbbb", title="older thing", created_at="2026-06-01T00:00:00Z"),
    ]
    journey = _fold(scopes=scopes, escalations=escs)["journey"]
    now = journey["now"]
    assert now["basis"] == "needs_attention"
    # the OLDEST (rank 1) drives the marker
    assert journey["needs_attention"]["items"][0]["age_rank"] == 1
    assert journey["needs_attention"]["items"][0]["need_id"] == "bbbbbbbbbbbb"


def test_journey_now_is_basis_aware_when_multiple_scopes_active():
    # two in_progress scopes, no open needs -> live_scope basis + plain multi note
    scopes = [_scope("s-a"), _scope("s-b")]
    signals = {"s-a": {"dispatched": True}, "s-b": {"dispatched": True}}
    journey = _fold(scopes=scopes, scope_signals=signals, escalations=[])["journey"]
    now = journey["now"]
    assert now["basis"] == "live_scope"
    assert now["active_scope_count"] == 2
    assert now["multiple_active"] is True
    assert now["active_note"]  # plainly says several are active — not a fake singular
    # it does not imply a singular state
    assert "2 pieces of work are in progress" in now["active_note"]


def test_journey_now_unavailable_when_board_source_absent():
    # scopes=None -> board unavailable -> now is honestly unavailable
    journey = _fold(scopes=None, escalations=[])["journey"]
    assert journey["now"]["basis"] == "unavailable"
    assert journey["arc"]["availability"] == "unavailable"


def test_journey_now_none_when_nothing_active():
    journey = _fold(scopes=[], escalations=[])["journey"]
    assert journey["now"]["basis"] == "none"
    assert journey["now"]["scope_id"] is None


# --- 5. needs-attention-translates-open-escalations (1:1) --------------------

def test_needs_attention_translates_open_escalations_one_to_one():
    escs = [
        _escalation("c1c1c1c1c1c1", title="thing one", created_at="2026-06-01T00:00:00Z"),
        _escalation("c2c2c2c2c2c2", title="thing two", created_at="2026-06-02T00:00:00Z"),
        _escalation(
            "resolved-one", title="done", created_at="2026-05-01T00:00:00Z",
            resolved_at="2026-05-02T00:00:00Z",
        ),
    ]
    journey = _fold(scopes=[_scope("s-1")], escalations=escs)["journey"]
    needs = journey["needs_attention"]
    counters = journey["counters"]
    # exactly one needs item + one detail per OPEN escalation (resolved excluded)
    assert needs["open_count"] == 2
    assert len(needs["items"]) == 2
    assert len(journey["need_details"]) == 2
    # the equalities (gate spec §6)
    assert counters["needs_source"] == "ok"
    assert counters["needs_open"] == counters["needs_translated"] == 2
    assert counters["needs_translated"] == counters["details_available"]
    # each item binds 1:1 to a detail by detail_ref
    for item in needs["items"]:
        assert item["detail_ref"] in journey["need_details"]
        assert item["need_id"] == item["detail_ref"]


# --- 6. needs-attention-unavailable-is-not-empty -----------------------------

def test_needs_attention_unavailable_is_not_empty():
    # escalations=None -> source unreachable
    journey = _fold(scopes=[_scope("s-1")], escalations=None)["journey"]
    needs = journey["needs_attention"]
    assert needs["availability"] == "unavailable"
    assert needs["message"] == cockpit_readmodel.NEEDS_UNAVAILABLE_MESSAGE
    assert needs["message"] != cockpit_readmodel.NEEDS_EMPTY_MESSAGE
    assert journey["counters"]["needs_source"] == "unavailable"


# --- 7. needs-attention-empty-is-clear ---------------------------------------

def test_needs_attention_empty_is_clear():
    journey = _fold(scopes=[_scope("s-1")], escalations=[])["journey"]
    needs = journey["needs_attention"]
    assert needs["availability"] == "ok"
    assert needs["open_count"] == 0
    assert needs["items"] == []
    assert needs["message"] == cockpit_readmodel.NEEDS_EMPTY_MESSAGE


# --- 8. plain-language-copy-has-zero-blocked-jargon --------------------------

def _all_ceo_text(journey: dict) -> list:
    texts: list = []
    arc = journey["arc"]
    texts += list(arc.get("stage_labels", {}).values())
    now = journey["now"]
    texts += [now.get("label"), now.get("active_note")]
    needs = journey["needs_attention"]
    texts.append(needs.get("message"))
    for scope in journey["scopes"]:
        texts.append(scope.get("goal"))
    for item in needs["items"]:
        texts += [
            item.get("headline"), item.get("plain_ask"),
            item.get("recommended_next_step"), item.get("why_now"),
        ]
    for detail in journey["need_details"].values():
        texts += [
            detail.get("title"), detail.get("what_this_means"),
            detail.get("why_ce_paused"), detail.get("if_you_continue"),
            detail.get("if_you_decline"), detail.get("ce_will_not"),
            detail.get("recommendation"),
        ]
    return texts


def test_plain_language_copy_has_zero_blocked_jargon():
    # seed with jargon-laden source text that MUST be scrubbed before render
    escs = [
        _escalation(
            "jargon1jargon", created_at="2026-06-01T00:00:00Z",
            title="Operator must ratify the escalation",
            decision_needed="approve the envelope or change the mutation_class",
            recommendation="follow the governance spine and refusal-chain",
        )
    ]
    scopes = [_scope("s-jargon", intent="probe a review outside the envelope")]
    journey = _fold(scopes=scopes, escalations=escs)["journey"]
    # the L2 self-audit counter
    assert journey["counters"]["plain_copy_findings"] == 0
    # and an independent sweep over every CEO-facing string
    findings = cockpit_readmodel.plain_text_findings(*_all_ceo_text(journey))
    assert findings == [], f"blocked jargon leaked into CEO copy: {findings}"


def test_machine_json_keys_may_keep_conserved_names():
    # source_ref / need_id keys are conserved on the machine record; they are not
    # CEO-facing prose. The detail still has a technical_source footer.
    escs = [_escalation("k1k1k1k1k1k1", title="a thing", created_at="2026-06-01T00:00:00Z",
                        source_ref="https://example/issues/1")]
    journey = _fold(scopes=[_scope("s-1")], escalations=escs)["journey"]
    detail = list(journey["need_details"].values())[0]
    assert "technical_source" in detail
    assert detail["technical_source"] == "https://example/issues/1"


# --- 9. detail-record-covers-non-engineer-explanation ------------------------

_DETAIL_FIELDS = (
    "need_id", "title", "what_this_means", "why_ce_paused",
    "if_you_continue", "if_you_decline", "ce_will_not", "recommendation",
    "technical_source",
)


def test_detail_record_covers_non_engineer_explanation():
    escs = [
        _escalation("budget1budget", title="spend hit the budget",
                    created_at="2026-06-01T00:00:00Z"),
        _escalation("unknown1unkno", title="something totally novel",
                    created_at="2026-06-02T00:00:00Z"),
    ]
    journey = _fold(scopes=[_scope("s-1")], escalations=escs)["journey"]
    for detail in journey["need_details"].values():
        for field in _DETAIL_FIELDS:
            assert field in detail, field
        # the explanation fields are non-empty and do NOT require the technical
        # source to be understood
        for field in ("what_this_means", "why_ce_paused", "if_you_continue",
                      "if_you_decline", "ce_will_not"):
            assert detail[field], field
    # the unknown class falls back to the conservative generic template
    novel = journey["need_details"]["unknown1unkno"]
    assert novel["what_this_means"] == cockpit_readmodel.NEEDS_GENERIC_PLAIN


def test_detail_understandable_without_technical_source():
    # a need with NO source_ref still has a complete plain explanation
    escs = [_escalation("nosrc1nosrc1", title="a decision", created_at="2026-06-01T00:00:00Z")]
    journey = _fold(scopes=[_scope("s-1")], escalations=escs)["journey"]
    detail = list(journey["need_details"].values())[0]
    assert detail["technical_source"] is None
    assert detail["what_this_means"]
    assert detail["why_ce_paused"]


# --- read-only: the fold mutates no inputs -----------------------------------

def test_fold_is_read_only_over_inputs():
    scopes = [_scope("s-1")]
    escs = [_escalation("ro1ro1ro1ro1", title="t", created_at="2026-06-01T00:00:00Z")]
    before_scopes = json.dumps(scopes, sort_keys=True)
    before_escs = json.dumps(escs, sort_keys=True)
    _fold(scopes=scopes, escalations=escs)
    assert json.dumps(scopes, sort_keys=True) == before_scopes
    assert json.dumps(escs, sort_keys=True) == before_escs
