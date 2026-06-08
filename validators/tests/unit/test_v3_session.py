"""Unit tests for the v3 session frame + unified status line (``v3_session``) — G-7.1.

Pure render + threshold + nudge logic over (stage skin, context meter, spend
meter). Asserts: the context meter consumes the harness % at the #157 thresholds
(never recomputes); the spend meter reuses the G-5 soft/hard ratios and folds the
real ``project_spend`` projection; the unified line fuses all three signals; the
checkpoint/`/clear` nudge is boundary-aware; the stage skin derives from the canon
(no third vocabulary); the surface carries no user `~/.claude` dependency.
"""
from __future__ import annotations

from decimal import Decimal

from creator_engine_validator import _versions as ver
from creator_engine_validator import v3_session as vs
from creator_engine_validator.runner.spend_gate import SOFT_BREACH_RATIO


# ---------------------------------------------------------------------------
# context meter — consumes the harness % at the #157 thresholds (warn 45 / urgent 60)
# ---------------------------------------------------------------------------
def test_context_meter_thresholds():
    assert vs.context_meter(10).state == "ok"
    assert vs.context_meter(44.9).state == "ok"
    assert vs.context_meter(45).state == "warn"
    assert vs.context_meter(59).state == "warn"
    assert vs.context_meter(60).state == "urgent"
    assert vs.context_meter(None).state == "unknown"
    # consumed verbatim — the meter never recomputes the number
    assert vs.context_meter(47).pct == 47.0


# ---------------------------------------------------------------------------
# spend meter — reuses the G-5 ratios verbatim (single source of truth)
# ---------------------------------------------------------------------------
def test_spend_meter_reuses_g5_ratios():
    assert vs.SPEND_SOFT_RATIO == SOFT_BREACH_RATIO == Decimal("0.8")
    assert vs.spend_meter(3, 5).state == "ok"        # 60%
    assert vs.spend_meter(4, 5).state == "soft"      # 80% == soft ratio
    assert vs.spend_meter(5, 5).state == "hard"      # 100%
    assert vs.spend_meter(6, 5).state == "hard"      # over cap
    assert vs.spend_meter(3, None).state == "unmetered"
    assert vs.spend_meter(3, 0).state == "unmetered"


def test_spend_meter_from_real_g5_projection():
    # fold the actual project_spend over a runtime_spend_ledger leaf set
    records = [
        {"record_type": "runtime_spend_ledger", "unit": "$", "amount": 2, "run_id": "r-1"},
        {"record_type": "runtime_spend_ledger", "unit": "$", "amount": 1.5, "run_id": "r-1"},
        {"record_type": "other", "unit": "$", "amount": 99, "run_id": "r-1"},  # ignored
        {"record_type": "runtime_spend_ledger", "unit": "$", "amount": 5, "run_id": "r-2"},  # other run
    ]
    m = vs.spend_meter_from_spine(records, 5, scope="run", unit="$", run_id="r-1")
    assert m.spent == Decimal("3.5") and m.cap == Decimal("5")
    assert m.state == "ok"  # 70%


# ---------------------------------------------------------------------------
# the unified status line — one surface fusing stage · context · spend
# ---------------------------------------------------------------------------
def test_status_line_fuses_three_signals():
    counts = {"Frame": 2, "Shape": 1, "Build": 1, "Review": 0, "Ship": 0}
    line = vs.render_status_line(counts, vs.context_meter(47), vs.spend_meter(4, 5))
    assert "Frame 2" in line and "Shape 1" in line   # stage skin
    assert "ctx 47%" in line and "⚠" in line          # context warn marker
    assert "spend $4/$5 80%" in line                  # spend segment


def test_status_line_stage_skin_is_canon_not_a_third_vocabulary():
    counts = {p: 0 for p in vs.coordination.COGNITIVE_PHASES}
    line = vs.render_status_line(counts, vs.context_meter(None), vs.spend_meter(0, None))
    # the phases in the line are exactly the canon COGNITIVE_PHASES (no coined set)
    for p in vs.coordination.COGNITIVE_PHASES:
        assert p in line
    assert "ctx —" in line and "spend —" in line       # unknown/unmetered render


# ---------------------------------------------------------------------------
# nudges — boundary-aware (never mid-output, except a hard spend breach)
# ---------------------------------------------------------------------------
def test_context_nudge_is_boundary_aware():
    ctx = vs.context_meter(63)  # urgent
    spend = vs.spend_meter(1, 5)
    assert vs.nudges(ctx, spend, at_boundary=True)       # surfaced at a boundary
    assert vs.nudges(ctx, spend, at_boundary=False) == []  # silent mid-output


def test_urgent_context_nudge_mentions_clear_and_resume():
    msgs = vs.nudges(vs.context_meter(70), vs.spend_meter(0, None), at_boundary=True)
    assert any("/clear" in m and "resume" in m for m in msgs)


def test_hard_spend_breach_always_surfaces():
    # a hard breach is a governance event — it surfaces even mid-output
    msgs = vs.nudges(vs.context_meter(10), vs.spend_meter(5, 5.0), at_boundary=False)
    assert any("pause + escalate" in m for m in msgs)
    # amounts render cleanly (no trailing zero) — consistent with the status line
    assert any("$5/$5)" in m for m in msgs) and not any("$5.0" in m for m in msgs)


def test_soft_spend_alert_is_boundary_aware():
    assert vs.nudges(vs.context_meter(10), vs.spend_meter(4, 5), at_boundary=False) == []
    assert vs.nudges(vs.context_meter(10), vs.spend_meter(4, 5), at_boundary=True)


# ---------------------------------------------------------------------------
# the assembled frame + project-level / CE-native posture
# ---------------------------------------------------------------------------
def test_render_session_is_banner_plus_line_plus_nudges():
    counts = {p: 0 for p in vs.coordination.COGNITIVE_PHASES}
    lines = vs.render_session(counts, context=vs.context_meter(65), spend=vs.spend_meter(5, 5),
                              repo="o/r", transport="cc-hooks", backend="gvisor")
    assert lines[0].startswith("◆ Creator Engine")
    assert "repo o/r" in lines[0] and "transport cc-hooks" in lines[0]
    assert "│" in lines[1]  # the unified status line
    assert len(lines) >= 3  # banner + line + at least one nudge (urgent ctx + hard spend)


def test_surface_is_v3_classified_and_project_level():
    # CE-native, project-level: a pure render with NO file/settings I/O — so it
    # carries no dependency on the user ~/.claude settings a governed seat excludes.
    assert ver.classify("v3_session") == ver.V3
    import inspect
    src = inspect.getsource(vs)
    for io_marker in ("open(", "read_text", "write_text", "Path.home", "os.environ", "settings.json"):
        assert io_marker not in src, f"session render must stay pure (found {io_marker!r})"
