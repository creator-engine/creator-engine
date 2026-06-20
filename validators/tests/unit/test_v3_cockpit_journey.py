"""Unit tests for the ce-ops#45 CEO-mode JOURNEY face (L3 Textual, render-only).

The elevation (supersedes the PR #230 minimum): the solo-founder **journey** is
the DEFAULT cockpit face and the expert ops board is demoted to a **Dev** face you
switch to with a persisted persona. The journey shows the FULL visual
development-arc / roadmap (a lane per canon stage with its plain description and
the project's work flowing through it), an honest "you are here" line, and the
first-class decision-inbox ("what needs you"). The view binds the precomputed
``snapshot["journey"]`` structures and renders; it parses nothing, derives
nothing, classifies nothing, and calls no loader — and it performs NO file I/O
(the persona is injected; the toggle persists through an injected callback).

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
    roadmap = v3_cockpit._journey_roadmap_text(journey)
    # the roadmap renders the precomputed scope goal verbatim
    assert journey["scopes"][0]["goal"] in roadmap
    header = v3_cockpit._journey_needs_header_text(journey)
    assert "What needs you" in header
    item = journey["needs_attention"]["items"][0]
    detail = journey["need_details"][item["detail_ref"]]
    detail_text = v3_cockpit._journey_detail_text(detail)
    assert detail["what_this_means"] in detail_text
    assert detail["why_ce_paused"] in detail_text


def test_journey_arc_marks_you_are_here_with_step_position():
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
    # the plain progress position (Build is stage 3 of 5)
    assert "Step 3 of 5" in arc


def test_journey_roadmap_renders_all_five_lanes_with_descriptions():
    from creator_engine_validator import v3_cockpit

    # s-ready -> Shape; s-draft (no intent) -> Frame.
    snapshot = _snapshot(
        scopes=[_scope("s-ready", intent="ship the meter"), _scope("s-draft", intent="")],
        escalations=[],
    )
    journey = snapshot["journey"]
    roadmap = v3_cockpit._journey_roadmap_text(journey)
    # every canon stage + its plain description appears on the one-screen picture
    for stage in cockpit_readmodel.coordination.COGNITIVE_PHASES:
        assert stage in roadmap
        assert journey["arc"]["stage_descriptions"][stage] in roadmap
    # the project arc: each scope's goal appears in the roadmap
    for jscope in journey["scopes"]:
        assert jscope["goal"] in roadmap


def test_journey_roadmap_is_unavailable_honestly():
    from creator_engine_validator import v3_cockpit

    journey = _snapshot(scopes=None, escalations=[])["journey"]
    text = v3_cockpit._journey_roadmap_text(journey)
    # honest: it does not fabricate a position when the board source is absent
    assert "I cannot" in text


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
            v3_cockpit._journey_roadmap_text(journey),
            v3_cockpit._journey_needs_header_text(journey),
            v3_cockpit._journey_detail_text(journey["need_details"][item["detail_ref"]]),
        ]
    )
    findings = cockpit_readmodel.plain_text_findings(rendered)
    assert findings == [], f"blocked jargon leaked into rendered CEO text: {findings}"


# --- the journey is the DEFAULT face -----------------------------------------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_journey_is_the_default_cockpit_face():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go():
        app = v3_cockpit.CockpitApp(snapshot)
        async with app.run_test() as _pilot:
            default_screen = type(app.screen).__name__
            arc = str(app.screen.query_one("#journey-arc").render())
            roadmap = str(app.screen.query_one("#journey-roadmap-text").render())
            needs_rows = app.screen.query_one("#journey-needs").row_count
            # the expert board is NOT mounted on the default face (it is demoted)
            board_present = len(app.screen.query("#board")) == 1
            return default_screen, arc, roadmap, needs_rows, board_present

    default_screen, arc, roadmap, needs_rows, board_present = asyncio.run(go())
    assert default_screen == "JourneyScreen"
    assert board_present is False
    # the arc shows all five canon stages on ONE screen
    for stage in cockpit_readmodel.coordination.COGNITIVE_PHASES:
        assert stage in arc
        assert stage in roadmap
    # the decision-inbox renders one row per open item
    assert needs_rows == snapshot["journey"]["needs_attention"]["open_count"]


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_dev_toggle_switches_to_the_board_and_back():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go():
        app = v3_cockpit.CockpitApp(snapshot)
        async with app.run_test() as pilot:
            first = type(app.screen).__name__
            await pilot.press("d")  # switch to the Dev / ops-board face
            await pilot.pause()
            on_board = type(app.screen).__name__
            board_present = len(app.screen.query("#board")) == 1
            await pilot.press("c")  # back to the founder journey face
            await pilot.pause()
            back = type(app.screen).__name__
            return first, on_board, board_present, back

    first, on_board, board_present, back = asyncio.run(go())
    assert first == "JourneyScreen"
    assert on_board == "BoardScreen"
    assert board_present
    assert back == "JourneyScreen"


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_persona_toggle_persists_through_the_injected_callback():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())
    persisted: list[str] = []

    async def go():
        app = v3_cockpit.CockpitApp(snapshot, on_persona_change=persisted.append)
        async with app.run_test() as pilot:
            await pilot.press("d")
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()
            return app.persona

    final = asyncio.run(go())
    # the view performs NO file I/O — it only calls the injected callback
    assert persisted == ["dev", "ceo"]
    assert final == "ceo"


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_app_opens_in_the_persisted_dev_persona():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go():
        app = v3_cockpit.CockpitApp(snapshot, persona="dev")
        async with app.run_test() as _pilot:
            return type(app.screen).__name__, len(app.screen.query("#board"))

    screen_name, board_count = asyncio.run(go())
    # a persisted Dev preference lands directly on the board, no toggle needed
    assert screen_name == "BoardScreen"
    assert board_count == 1


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_unknown_persona_falls_back_to_the_default_face():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go():
        app = v3_cockpit.CockpitApp(snapshot, persona="nonsense")
        async with app.run_test() as _pilot:
            return type(app.screen).__name__

    assert asyncio.run(go()) == "JourneyScreen"


# --- the decision-inbox is a first-class, titled surface ---------------------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_decision_inbox_is_a_first_class_titled_surface():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go():
        app = v3_cockpit.CockpitApp(snapshot)
        async with app.run_test() as _pilot:
            inbox = app.screen.query_one("#journey-inbox")
            return str(inbox.border_title)

    title = asyncio.run(go())
    assert "What needs you" in title


# --- click-or-focus-opens-precomputed-detail ---------------------------------

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
            table = app.screen.query_one("#journey-needs")
            table.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            modal = app.screen
            text = str(modal.query_one("#journey-detail-text").render())
            return type(modal).__name__, text

    modal_name, text = asyncio.run(go())
    assert modal_name == "JourneyDetailScreen"
    # the modal shows the PRECOMPUTED detail (looked up by detail_ref)
    assert expected_detail["what_this_means"] in text
    assert expected_detail["why_ce_paused"] in text


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_journey_row_carries_only_the_precomputed_detail_ref():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go():
        app = v3_cockpit.CockpitApp(snapshot)
        async with app.run_test() as _pilot:
            return list(app.screen._need_rows)

    refs = asyncio.run(go())
    expected = [
        item["detail_ref"]
        for item in snapshot["journey"]["needs_attention"]["items"]
    ]
    assert refs == expected
