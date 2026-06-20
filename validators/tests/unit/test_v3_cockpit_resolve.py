"""Unit tests for ce-ops#45 Slice 2 — resolve a decision from the cockpit inbox.

The interactive governance write-seam: the decision-inbox can RESOLVE a decision,
but ONLY by actuating the existing canonical escalation-resolve gate
(``v3_cli.resolve_escalation``) through an injected callback, after a form-echo
confirmation ([[ce-authority-attaches-to-form]]). The cockpit view writes no
governance state itself and never bypasses the gate. When no resolve seam is
wired (the seeded demo / read-only), the affordance is hidden.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import v3_cli
from creator_engine_validator.runner import cockpit_readmodel

_HAS_TEXTUAL = importlib.util.find_spec("textual") is not None


def _open_escalation(root: Path, esc_id: str = "operator-call") -> str:
    rc = v3_cli.main([
        "escalation", "open", "--id", esc_id,
        "--title", "Spend decision",
        "--decision", "Raise the budget, or stop here?",
        "--recommend", "Stop and re-scope before raising the budget.",
        "--root", str(root),
    ])
    assert rc == 0
    return esc_id


def _live_snapshot(root: Path) -> dict:
    return cockpit_readmodel.snapshot_from_roots(root, environ={})


def _resolution_for(root: Path):
    return lambda need_id: v3_cli.resolve_escalation(
        root, need_id, resolution="Recorded by the founder from the cockpit"
    )


def _escalation_on_disk(root: Path, esc_id: str) -> dict:
    return yaml.safe_load((root / "escalations" / f"{esc_id}.yaml").read_text(encoding="utf-8"))


# --- the form-echo is plain (no model text, zero blocked jargon) -------------

def test_resolve_form_echo_renders_the_plain_form():
    from creator_engine_validator import v3_cockpit

    detail = {
        "need_id": "x", "title": "A budget decision is waiting for you",
        "recommendation": "Stop and re-scope before raising the budget.",
    }
    text = v3_cockpit._journey_resolve_form_text(detail)
    assert detail["title"] in text
    assert detail["recommendation"] in text
    assert "Confirm (y)" in text
    assert "Cancel" in text


def test_resolve_form_echo_has_zero_blocked_jargon():
    from creator_engine_validator import v3_cockpit

    # jargon-laden source -> L2 scrubs it -> the form-echo stays plain
    snapshot = cockpit_readmodel.fold_snapshot(
        scopes=[{"kind": "scope-record", "scope_id": "s-1", "intent": "x",
                 "acceptance_criteria": ["ok"], "appetite": {"amount": 5, "unit": "$"},
                 "mutation_class": "code"}],
        escalations=[{
            "kind": "escalation-record", "record_type": "escalation", "schema_version": "1",
            "escalation_id": "j1j1j1j1j1j1", "title": "Operator must ratify the escalation",
            "decision_needed": "approve the envelope or change the mutation_class",
            "recommendation": "follow the governance spine and refusal-chain",
            "created_at": "2026-06-01T00:00:00Z",
        }],
    )
    item = snapshot["journey"]["needs_attention"]["items"][0]
    detail = snapshot["journey"]["need_details"][item["detail_ref"]]
    text = v3_cockpit._journey_resolve_form_text(detail)
    assert cockpit_readmodel.plain_text_findings(text) == []


# --- the cockpit NEVER actuates the gate directly (only via the callback) -----

def test_cockpit_view_never_actuates_the_gate_directly():
    pkg = Path(v3_cli.__file__).resolve().parent
    source = (pkg / "v3_cockpit.py").read_text(encoding="utf-8")
    for forbidden in (
        "resolve_escalation(",     # never CALLS the gate function directly
        "_write_escalation",       # never writes the record
        "escalations/",            # never touches the escalation store
        "import v3_cli",
        "from . import v3_cli",
        "from .v3_cli",
    ):
        assert forbidden not in source, (
            f"the cockpit view must actuate the gate ONLY via the injected callback; "
            f"found {forbidden!r} in v3_cockpit.py"
        )


# --- the textual write-seam drives the canonical gate ------------------------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_recording_a_decision_actuates_the_gate_and_clears_the_inbox(tmp_path):
    from creator_engine_validator import v3_cockpit

    esc_id = _open_escalation(tmp_path)
    snapshot = _live_snapshot(tmp_path)
    assert snapshot["journey"]["needs_attention"]["open_count"] == 1

    async def go():
        app = v3_cockpit.CockpitApp(
            snapshot,
            reload=lambda: _live_snapshot(tmp_path),
            on_resolve=_resolution_for(tmp_path),
        )
        async with app.run_test(size=(120, 40)) as pilot:
            before = app.screen.query_one("#journey-needs").row_count
            app.screen.query_one("#journey-needs").focus()
            await pilot.pause()
            await pilot.press("enter")  # open the read-only detail
            await pilot.pause()
            detail = type(app.screen).__name__
            await pilot.press("r")      # record my decision -> form-echo
            await pilot.pause()
            confirm = type(app.screen).__name__
            await pilot.press("y")      # confirm -> actuate the canonical gate
            await pilot.pause()
            back = type(app.screen).__name__
            after = app.screen.query_one("#journey-needs").row_count
            return before, detail, confirm, back, after

    before, detail, confirm, back, after = asyncio.run(go())
    assert before == 1
    assert detail == "JourneyDetailScreen"
    assert confirm == "ResolveConfirmScreen"
    assert back == "JourneyScreen"          # both modals closed
    assert after == 0                        # the resolved item left the inbox

    # the canonical gate WROTE the resolution (via the seam, schema-validated)
    record = _escalation_on_disk(tmp_path, esc_id)
    assert "resolved_at" in record
    assert record["resolution"] == "Recorded by the founder from the cockpit"


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_cancelling_the_form_echo_resolves_nothing(tmp_path):
    from creator_engine_validator import v3_cockpit

    esc_id = _open_escalation(tmp_path)
    snapshot = _live_snapshot(tmp_path)

    async def go():
        app = v3_cockpit.CockpitApp(
            snapshot,
            reload=lambda: _live_snapshot(tmp_path),
            on_resolve=_resolution_for(tmp_path),
        )
        async with app.run_test(size=(120, 40)) as pilot:
            app.screen.query_one("#journey-needs").focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("r")
            await pilot.pause()
            await pilot.press("escape")  # cancel the form-echo
            await pilot.pause()
            return type(app.screen).__name__

    screen = asyncio.run(go())
    assert screen == "JourneyDetailScreen"  # back on the detail, nothing recorded
    record = _escalation_on_disk(tmp_path, esc_id)
    assert "resolved_at" not in record


# --- the composition root wires the seam in LIVE mode, not in the demo --------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_cockpit_tui_wires_the_resolve_gate_in_live_not_demo(tmp_path, monkeypatch):
    from creator_engine_validator import v3_cockpit

    esc_id = _open_escalation(tmp_path)
    captured: dict = {}

    def fake_run_app(snapshot, *, reload=None, watch_paths=(), persona="ceo",
                     on_persona_change=None, on_resolve=None):
        captured["on_resolve"] = on_resolve
        return 0

    monkeypatch.setattr(v3_cockpit, "run_app", fake_run_app)

    # LIVE: the resolve seam is wired and actuates the canonical gate
    monkeypatch.delenv("CE_DEMO", raising=False)
    assert v3_cli.main(["cockpit", "--root", str(tmp_path)]) == 0
    on_resolve = captured["on_resolve"]
    assert callable(on_resolve)
    result = on_resolve(esc_id)
    assert result["ok"] is True
    record = _escalation_on_disk(tmp_path, esc_id)
    assert "resolved_at" in record
    assert record["resolution"] == v3_cli.COCKPIT_RESOLUTION_NOTE

    # DEMO: read-only — NO resolve seam is wired
    captured.clear()
    monkeypatch.setenv("CE_DEMO", "1")
    assert v3_cli.main(["cockpit", "--root", str(tmp_path)]) == 0
    assert captured["on_resolve"] is None


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_resolve_is_hidden_when_no_seam_is_wired():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed

    # the seeded demo carries an open need but NO resolve callback -> read-only
    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go():
        app = v3_cockpit.CockpitApp(snapshot)  # no on_resolve
        async with app.run_test(size=(120, 40)) as pilot:
            enabled = app.resolve_enabled
            app.screen.query_one("#journey-needs").focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            on_detail = type(app.screen).__name__
            await pilot.press("r")  # must be a no-op: the seam is not wired
            await pilot.pause()
            still = type(app.screen).__name__
            return enabled, on_detail, still

    enabled, on_detail, still = asyncio.run(go())
    assert enabled is False
    assert on_detail == "JourneyDetailScreen"
    assert still == "JourneyDetailScreen"  # no form-echo opened
