from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "scripts" / "gen-controller-bootstrap.py"

spec = importlib.util.spec_from_file_location("gen_controller_bootstrap", MODULE_PATH)
assert spec is not None
gen_controller_bootstrap = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gen_controller_bootstrap)


def _load_ssot():
    return gen_controller_bootstrap.load_ssot(gen_controller_bootstrap.DEFAULT_SSOT)


def test_ssot_validates():
    ssot, ssot_path, ssot_hash = _load_ssot()

    gen_controller_bootstrap.validate_ssot(ssot)
    assert ssot_path == "docs/design/controller-bootstrap-ssot.json"
    assert len(ssot_hash) == 64


def test_overlay_section_present():
    ssot, _ssot_path, _ssot_hash = _load_ssot()

    assert "controller_knowledge_overlay" in ssot
    assert ssot["controller_knowledge_overlay"]["startup_sequence"]


def test_required_overlay_keys():
    ssot, _ssot_path, _ssot_hash = _load_ssot()
    overlay = ssot["controller_knowledge_overlay"]

    assert set(overlay) >= {
        "startup_sequence",
        "pre_dispatch_checklist",
        "harvest_sequence",
        "subagent_model_routing",
        "preflight_discipline",
        "g5_body_line_rule",
        "new_ce_group_coupling",
    }


def test_build_files_produces_expected_keys():
    ssot, ssot_path, ssot_hash = _load_ssot()

    files = gen_controller_bootstrap.build_files(ssot, "all", ssot_path, ssot_hash)

    assert Path("codex/AGENTS.md") in files
    assert Path("claude/CLAUDE.md") in files


def test_overlay_content_in_rendered_output():
    ssot, ssot_path, ssot_hash = _load_ssot()

    files = gen_controller_bootstrap.build_files(ssot, "all", ssot_path, ssot_hash)
    for rel_path in (Path("codex/AGENTS.md"), Path("claude/CLAUDE.md")):
        content = files[rel_path]
        assert "## Controller Knowledge Overlay" in content
        assert "Read SSOT-grounded bootstrap before accepting any task." in content
        assert "### Startup Sequence" in content


def test_generator_refuses_live_paths():
    for path in (
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / ".claude" / "agents",
        REPO_ROOT,
    ):
        with pytest.raises(SystemExit):
            gen_controller_bootstrap.ensure_safe_out_dir(path)


def test_deterministic_output():
    ssot, ssot_path, ssot_hash = _load_ssot()

    first = gen_controller_bootstrap.build_files(ssot, "all", ssot_path, ssot_hash)
    second = gen_controller_bootstrap.build_files(ssot, "all", ssot_path, ssot_hash)

    assert first == second


def test_missing_overlay_section_fails_closed():
    ssot, _ssot_path, _ssot_hash = _load_ssot()
    missing_overlay = copy.deepcopy(ssot)
    missing_overlay.pop("controller_knowledge_overlay")

    with pytest.raises(SystemExit):
        gen_controller_bootstrap.validate_ssot(missing_overlay)
