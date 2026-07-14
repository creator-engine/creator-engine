from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_validate_wires_release_smoke_gate_for_pr_and_merge_queue():
    workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    assert "Creator Engine validator — release smoke-evidence gate" in workflow
    assert "github.event_name == 'pull_request' || github.event_name == 'merge_group'" in workflow
    assert "verify-release-smoke-evidence --base \"${comparison_base}\"" in workflow


def test_local_preflight_wires_the_same_release_smoke_gate():
    preflight = (ROOT / "validators/creator_engine_validator/pr_preflight.py").read_text(encoding="utf-8")
    assert "Release smoke-evidence gate" in preflight
    assert "verify-release-smoke-evidence" in preflight
