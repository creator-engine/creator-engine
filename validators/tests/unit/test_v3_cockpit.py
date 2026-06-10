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
