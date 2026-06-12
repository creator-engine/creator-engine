"""Unit tests for the Cockpit L3 Textual view + the textual-free CLI paths (v3.5-B.1).

The principle-6 law in testable form (cluster §0.4):

* ``ce cockpit --json`` dumps the L2 snapshot with ``textual`` NEVER imported
  (the future-GUI seam is a first-class invocation);
* every NON-cockpit path (``--list-checks``; non-cockpit ``ce`` subcommands)
  imports neither ``textual`` nor ``watchfiles``;
* the L3 module binds ONLY to L2 snapshots — a source-level assertion proves it
  performs no direct spine/registry read;
* L3 smoke: the app constructs and renders the persistent ``CE_DEMO`` watermark
  (``skipif``-absent guard for minimal local envs only — CI installs the extra
  and RUNS this).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

VALIDATORS_DIR = Path(__file__).resolve().parents[2]
PKG_DIR = VALIDATORS_DIR / "creator_engine_validator"

_HAS_TEXTUAL = importlib.util.find_spec("textual") is not None


def _run(code: str, *, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(VALIDATORS_DIR), **(extra_env or {})}
    return subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )


# --- principle 6.4: the --json path is a textual-free first-class invocation --

def test_cockpit_json_demo_runs_without_textual(tmp_path):
    code = (
        "import sys\n"
        "from creator_engine_validator import v3_cli\n"
        f"rc = v3_cli.main(['cockpit', '--json', '--root', {str(tmp_path)!r}])\n"
        "assert rc == 0, rc\n"
        "assert 'textual' not in sys.modules, 'textual leaked into the --json path'\n"
        "assert 'watchfiles' not in sys.modules, 'watchfiles leaked into the --json path'\n"
    )
    proc = _run(code, extra_env={"CE_DEMO": "1"})
    assert proc.returncode == 0, proc.stderr
    snapshot = json.loads(proc.stdout)
    assert snapshot["source"]["demo"] is True
    assert snapshot["source"]["watermark"].startswith("DEMO")
    assert snapshot["board"]["cards"], "the demo board must carry cards"
    assert snapshot["escalations"]["open_count"] >= 1
    assert len(snapshot["dispatches"]["entries"]) >= 2


def test_cockpit_json_live_runs_without_textual(tmp_path):
    code = (
        "import sys\n"
        "from creator_engine_validator import v3_cli\n"
        f"rc = v3_cli.main(['cockpit', '--json', '--root', {str(tmp_path)!r}])\n"
        "assert rc == 0, rc\n"
        "assert 'textual' not in sys.modules\n"
        "assert 'watchfiles' not in sys.modules\n"
    )
    proc = _run(code, extra_env={"CE_DEMO": "0", "CE_LEDGER_ROOT": ""})
    assert proc.returncode == 0, proc.stderr
    snapshot = json.loads(proc.stdout)
    assert snapshot["source"]["demo"] is False


# --- non-cockpit import paths stay textual-free (cluster §0.5) ---------------

def test_list_checks_imports_no_textual():
    code = (
        "import sys\n"
        "from creator_engine_validator import cli\n"
        "rc = cli.main(['--list-checks'])\n"
        "assert rc == 0, rc\n"
        "assert 'textual' not in sys.modules, '--list-checks must not import textual'\n"
        "assert 'watchfiles' not in sys.modules\n"
    )
    proc = _run(code)
    assert proc.returncode == 0, proc.stderr


def test_non_cockpit_ce_subcommand_imports_no_textual(tmp_path):
    code = (
        "import sys\n"
        "from creator_engine_validator import v3_cli\n"
        f"rc = v3_cli.main(['status', '--root', {str(tmp_path)!r}])\n"
        "assert rc == 0, rc\n"
        "assert 'textual' not in sys.modules, 'non-cockpit ce paths must not import textual'\n"
        "assert 'watchfiles' not in sys.modules\n"
    )
    proc = _run(code)
    assert proc.returncode == 0, proc.stderr


# --- principle 6.5: L3 binds only — no direct spine/registry reads -----------

def test_l3_source_performs_no_direct_reads():
    source = (PKG_DIR / "v3_cockpit.py").read_text(encoding="utf-8")
    forbidden = (
        "runtime_evidence_spine",
        "evidence_sink",
        "pco_allocator",
        "cockpit_readmodel",
        "cockpit_demo_seed",
        "import yaml",
        "safe_load",
        "open(",
        "read_text",
        "active-work-ledger",
    )
    for token in forbidden:
        assert token not in source, (
            f"L3 must bind to the provided snapshot only; found direct-read "
            f"token {token!r} in v3_cockpit.py"
        )
    assert "textual" in source, "v3_cockpit IS the Textual view"


# --- rail rendering for B2 live-feed additions ------------------------------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_rails_render_escalations_and_dispatches():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed, cockpit_readmodel

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())
    left = v3_cockpit._left_rail_text(snapshot)
    right = v3_cockpit._right_rail_text(snapshot)

    assert "Dispatches" in left
    assert "gate-uploads · spawned · code · cap $12.0 per_run" in left
    assert "ship-pr-294 · collected" in left
    assert "AWAITING OPERATOR" in right
    assert "Spend hard-breach needs Operator decision" in right
    assert "recommend: Halt and re-scope before raising the cap." in right


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_rails_render_unavailable_new_feeds_honestly():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_readmodel

    snapshot = cockpit_readmodel.fold_snapshot(demo=False)
    assert "Dispatches (unavailable)" in v3_cockpit._left_rail_text(snapshot)
    assert "escalation source unavailable" in v3_cockpit._right_rail_text(snapshot)


# --- v3.1-B.7: the L3 cost rail render (render-only; computation stays in L2) -

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_meter_strip_renders_cost_rail_with_both_tiers():
    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed, cockpit_readmodel

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())
    text = v3_cockpit._meter_strip_text(snapshot)
    # The fleet cost line: measured $ MEASURED + the unpriced (subscription) count.
    assert "cost $13.30 MEASURED" in text
    assert "unpriced (subscription)" in text
    # A MEASURED scope shows its $ and model; the explicit subscription run shows
    # NO $ at all — never the silent-$0 lie the honesty tier exists to prevent.
    assert "spend-hard-breach $10.00" in text
    assert "subscription-seat unpriced (subscription)" in text
    assert "subscription-seat $0" not in text
    # The headroom FLOOR note rides the rail.
    assert "FLOOR on true fleet cost" in text


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_meter_strip_declares_cost_truncation_never_silent():
    from creator_engine_validator import v3_cockpit

    # 8 measured scopes -> top 6 by $ shown, the remaining 2 DECLARED truncated.
    scopes = [
        {
            "scope_id": f"run-{i:02d}",
            "tier": "MEASURED",
            "spend": float(i),
            "leaf_count": 1,
            "models": ["claude-opus-4-8"],
        }
        for i in range(1, 9)
    ]
    snapshot = {
        "meters": {
            "spend": {},
            "token_rate": {},
            "context": {},
            "subscription_headroom": {},
            "banners": [],
            "cost": {
                "badge": "MEASURED",
                "unit": "$",
                "scopes": scopes,
                "fleet": {"measured_spend": 36.0, "unpriced_run_count": 0},
                "headroom_note": "all 8 runs are $-measured",
            },
        }
    }
    text = v3_cockpit._meter_strip_text(snapshot)
    assert "more scopes truncated" in text
    assert "top 6 by $ shown" in text
    # The cheapest scopes are the ones dropped (highest $ retained).
    assert "run-08 $8.00" in text
    assert "run-01 $1.00" not in text


# --- L3 smoke (CI-exercised; skipif-absent for minimal local envs only) ------

@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_app_constructs_and_renders_watermark_and_board():
    import asyncio

    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_demo_seed, cockpit_readmodel

    snapshot = cockpit_readmodel.fold_snapshot(demo=True, **cockpit_demo_seed.seed())

    async def go() -> tuple[str, int]:
        app = v3_cockpit.CockpitApp(snapshot)
        async with app.run_test() as _pilot:
            watermark = app.query_one("#watermark").render()
            table = app.query_one("#board")
            return str(watermark), table.row_count

    watermark_text, row_count = asyncio.run(go())
    assert cockpit_readmodel.DEMO_WATERMARK in watermark_text
    assert row_count == len(snapshot["board"]["cards"])


@pytest.mark.skipif(not _HAS_TEXTUAL, reason="cockpit extra not installed (minimal local env)")
def test_app_live_mode_has_no_watermark_widget():
    import asyncio

    from creator_engine_validator import v3_cockpit
    from creator_engine_validator.runner import cockpit_readmodel

    snapshot = cockpit_readmodel.fold_snapshot(demo=False)

    async def go() -> int:
        app = v3_cockpit.CockpitApp(snapshot)
        async with app.run_test() as _pilot:
            return len(app.query("#watermark"))

    assert asyncio.run(go()) == 0
