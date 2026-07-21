"""No-op-resistant wiring tests for T4's local-gate CI migration."""

from __future__ import annotations

from pathlib import Path

import yaml


_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "validate.yml"
_DIFF_EVENT_GUARD = "${{ github.event_name == 'pull_request' || github.event_name == 'merge_group' }}"
_COMPARISON_BASE = "${{ steps.live-base.outputs.comparison_base }}"


def _steps() -> list[dict]:
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    return workflow["jobs"]["validate"]["steps"]


def _step(name: str) -> dict:
    matches = [step for step in _steps() if step.get("name") == name]
    assert len(matches) == 1, f"expected exactly one {name!r} step, found {len(matches)}"
    return matches[0]


def test_t4_current_surface_gate_steps_each_appear_once_after_install():
    install_index = next(
        index for index, step in enumerate(_steps()) if step.get("name") == "Install validator test deps (offline, from dev wheelhouse)"
    )
    pytest_index = next(
        index
        for index, step in enumerate(_steps())
        if step.get("name") == "Creator Engine validator — pytest suite (offline)"
    )
    expected = {
        "Creator Engine validator — public-docs confidentiality gate": "scan-public-docs-confidentiality .",
        "Creator Engine validator — documented verbs gate": "scan-documented-verbs .",
        "Creator Engine validator — control-plane portability gate": "scan-portability-plane .",
        "Creator Engine validator — support-corpus confidentiality gate": "scan-support-corpus .",
        "Creator Engine validator — fleet manifest guard": "preflight-gate fleet-manifest --repo-root .",
    }

    for name, exact_tokens in expected.items():
        step = _step(name)
        assert "PYTHONPATH=validators python -m creator_engine_validator" in step["run"]
        assert exact_tokens in step["run"]
        index = _steps().index(step)
        assert install_index < index < pytest_index


def test_t4_aggregate_examples_step_is_explicit_and_not_a_local_diagnostic():
    step = _step("Creator Engine validator — check-examples aggregate gate")
    assert "PYTHONPATH=validators python -m creator_engine_validator check-examples" in step["run"]
    assert "if " not in step


def test_t4_diff_gates_have_live_comparison_base_and_pr_merge_group_guard():
    expected = {
        "Creator Engine validator — brain current-tail PR-diff gate": (
            "preflight-gate brain-current-tail --comparison-base \"${comparison_base}\"",
            "--live-base \"${live_base}\"",
        ),
        "Creator Engine validator — brain append-intent XOR PR-diff gate": (
            "preflight-gate brain-append-intent-xor --comparison-base \"${comparison_base}\"",
        ),
        "Creator Engine validator — signed-artifact hash-pin PR-diff gate": (
            "verify-signed-artifact-pins --base \"${comparison_base}\" .",
        ),
        "Creator Engine validator — dual-format sync PR-diff gate": (
            "verify-dual-format-sync --base \"${comparison_base}\" .",
        ),
    }

    for name, exact_tokens in expected.items():
        step = _step(name)
        assert step.get("if") == _DIFF_EVENT_GUARD
        assert step.get("env", {}).get("COMPARISON_BASE") == _COMPARISON_BASE
        assert 'comparison_base="${COMPARISON_BASE}"' in step["run"]
        assert "live comparison base was not resolved" in step["run"] or "live comparison base and live base ref are required" in step["run"]
        for token in exact_tokens:
            assert token in step["run"]

    current_tail = _step("Creator Engine validator — brain current-tail PR-diff gate")
    assert current_tail.get("env", {}).get("LIVE_BASE") == "origin/${{ steps.live-base.outputs.base_ref }}"


def test_t4_preserves_read_only_validate_permissions_and_does_not_call_full_preflight():
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert workflow["permissions"] == {"contents": "read", "pull-requests": "read"}
    assert "permissions" not in workflow["jobs"]["validate"]
    assert "validate-pr" not in _WORKFLOW_PATH.read_text(encoding="utf-8")
