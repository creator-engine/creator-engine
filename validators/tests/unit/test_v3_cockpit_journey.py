"""Unit tests for the ce-ops#45 CEO-mode JOURNEY view (L3 Textual, render-only).

The journey screen is a SECOND screen over the SAME L2 snapshot, reachable by a
key binding — the expert ops board stays the DEFAULT screen (no product mode
switcher, no default change). The view binds the precomputed
``snapshot["journey"]`` structures and renders; it parses nothing, derives
nothing, classifies nothing, and calls no loader. Detail comes only from the
precomputed ``need_details[detail_ref]``.

Smoke tests seed ``CockpitApp(snapshot)`` and drive ``app.run_test()``.
"""

from __future__ import annotations

import asyncio
import importlib.util

import pytest

from creator_engine_validator.runner import cockpit_readmodel

_HAS_TEXTUAL = importlib.util.find_spec("textual") is not None


def _scope(scope_id: str, *, intent: str = "do a thing") -> dict:
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
    return rec


def _snapshot(**kwargs) -> dict:
    return cockpit_readmodel.fold_snapshot(**kwargs)


# --- pure formatter helpers compute nothing (textual not required) -----------

def test_journey_helpers_bind_only_precomputed_l2_strings():
    # The view's pure formatters read snapshot["journey"] strings verbatim.
    from creator_engine_validator import v3_cockpit

    snapshot = _snapshot(
        scopes=[_scope("s-1", intent="ship the thing")],
        scope_signals={"s-1": {"dispatched": True}},
        escalations=[_escalation("d1d1d1d1d1d1", title="needs you",
                                 created_at="2026-06-01T00:00:00Z")],
    )
    journey = snapshot["journey"]
    arc = v3_cockpit._journey_arc_text(journey)
    for stage in journey["arc"]["stages"]:
        assert stage in arc
    now = v3_cockpit._journey_now_text(journey)
    assert journey["now"]["label"] in now
    scopes = v3_cockpit._journey_scopes_text(journey)
    assert journey["scopes"][0]["goal"] in scopes
    header = v3_cockpit._journey_needs_header_text(journey)
    assert "What needs you" in header
    item = journey["needs_attention"]["items"][0]
    detail = journey["need_details"][item["detail_ref"]]
    detail_text = v3_cockpit._journey_detail_text(detail)
    assert detail["what_this_means"] in detail_text
    assert detail["why_ce_paused"] in detail_text


def test_journey_arc_marks_you_are_here_on_live_basis():
    from creator_engine_validator import v3_cockpit

    # one in_progress scope, no open needs -> live_scope basis -> Build marked
    snapshot = _snapshot(
        scopes=[_scope("s-1")],
        scope_signals={"s-1": {"dispatched": True}},
        escalations=[],
    )
    journey = snapshot["journey"]
    assert journey["now"]["basis"] == "live_scope"
    assert journey["now"]["stage"] == "Build"
    arc = v3_cockpit._journey_arc_text(journey)
    assert "▶ Build" in arc


def test_journey_needs_header_is_honest_empty_vs_unavailable():
    from creator_engine_validator import v3_cockpit

    empty = _snapshot(scopes=[_scope("s-1")], escalations=[])["journey"]
    assert cockpit_readmodel.NEEDS_EMPTY_MESSAGE in v3_cockpit._journey_needs_header_text(empty)

    unavailable = _snapshot(scopes=[_scope("s-1")], escalations=None)["journey"]
    assert (
        cockpit_readmodel.NEEDS_UNAVAILABLE_MESSAGE
        in v3_cockpit._journey_needs_header_text(unavailable)
    )


# --- the rendered CEO text carries zero blocked jargon -----------------------

def test_rendered_l3_journey_text_has_zero_blocked_jargon():
    from creator_engine_validator import v3_cockpit

    snapshot = _snapshot(
        scopes=[_scope("s-jargon", intent="probe a review outside the envelope")],
        escalations=[
            _escalation(
                "j1j1j1j1j1j1", created_at="2026-06-01T00:00:00Z",
                title="Operator must ratify the escalation",
                decision_needed="approve the envelope or change the mutation_class",
                recommendation="follow the governance spine and refusal-chain",
            )
        ],
    )
    journey = snapshot["journey"]
    item = journey["needs_attention"]["items"][0]
    rendered = "\n".join(
        [
            v3_cockpit._journey_arc_text(journey),
            v3_cockpit._journey_now_text(journey),
            v3_cockpit._journey_scopes_text(journey),
            v3_cockpit._journey_needs_header_text(journey),
            v3_cockpit._journey_detail_text(journey["need_details"][item["detail_ref"]]),
        ]
    )
    findings = cockpit_readmodel.plain_text_findings(rendered)
    assert findings == [], f"blocked jargon leaked into rendered CEO text: {findings}"


# --- 10. textual-renders-one-screen-journey ----------------------------------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_textual_renders_one_screen_journey():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go():
        app = v3_cockpit.CockpitApp(snapshot)
        async with app.run_test() as pilot:
            # the board is the DEFAULT screen (no default change)
            default_screen = type(app.screen).__name__
            await pilot.press("j")
            await pilot.pause()
            journey_screen = app.screen
            arc = str(journey_screen.query_one("#journey-arc").render())
            now = str(journey_screen.query_one("#journey-now").render())
            needs_rows = journey_screen.query_one("#journey-needs").row_count
            return default_screen, type(journey_screen).__name__, arc, now, needs_rows

    default_screen, screen_name, arc, now, needs_rows = asyncio.run(go())
    assert default_screen == "CockpitScreen" or default_screen != "JourneyScreen"
    assert screen_name == "JourneyScreen"
    # the arc shows all five canon stages on ONE screen
    for stage in cockpit_readmodel.coordination.COGNITIVE_PHASES:
        assert stage in arc
    assert "You are here" in now
    # the needs list renders one row per open item
    assert needs_rows == snapshot["journey"]["needs_attention"]["open_count"]


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_board_stays_the_default_screen():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go():
        app = v3_cockpit.CockpitApp(snapshot)
        async with app.run_test() as pilot:
            # default screen is NOT the journey screen
            before = type(app.screen).__name__
            # the board's signature widget exists by default
            board_present = len(app.query("#board")) == 1
            await pilot.press("j")
            await pilot.pause()
            on_journey = type(app.screen).__name__ == "JourneyScreen"
            await pilot.press("escape")  # back to board
            await pilot.pause()
            after = type(app.screen).__name__
            return before, board_present, on_journey, after

    before, board_present, on_journey, after = asyncio.run(go())
    assert before != "JourneyScreen"
    assert board_present
    assert on_journey
    assert after == before  # escape returns to the default board screen


# --- 11. click-or-focus-opens-precomputed-detail -----------------------------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_selecting_a_need_opens_its_precomputed_detail():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())
    item = snapshot["journey"]["needs_attention"]["items"][0]
    expected_detail = snapshot["journey"]["need_details"][item["detail_ref"]]

    async def go():
        app = v3_cockpit.CockpitApp(snapshot)
        async with app.run_test() as pilot:
            await pilot.press("j")
            await pilot.pause()
            journey_screen = app.screen
            table = journey_screen.query_one("#journey-needs")
            table.focus()
            await pilot.pause()
            # selecting the focused row (Enter) opens the precomputed detail
            await pilot.press("enter")
            await pilot.pause()
            modal = app.screen
            text = str(modal.query_one("#journey-detail-text").render())
            return type(modal).__name__, text

    modal_name, text = asyncio.run(go())
    assert modal_name == "JourneyDetailScreen"
    # the modal shows the PRECOMPUTED detail (looked up by detail_ref), not a
    # re-derivation
    assert expected_detail["what_this_means"] in text
    assert expected_detail["why_ce_paused"] in text


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_journey_row_carries_only_the_precomputed_detail_ref():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go():
        app = v3_cockpit.CockpitApp(snapshot)
        async with app.run_test() as pilot:
            await pilot.press("j")
            await pilot.pause()
            screen = app.screen
            # the screen stores ONLY the precomputed detail_refs from L2 — no
            # parsing, no source-ref decoding
            return list(screen._need_rows)

    refs = asyncio.run(go())
    expected = [
        item["detail_ref"]
        for item in snapshot["journey"]["needs_attention"]["items"]
    ]
    assert refs == expected
