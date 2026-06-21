"""Workflow/template guard for work-sizing floor CI wiring."""

from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VALIDATE_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "validate.yml"
_PR_TEMPLATE = _REPO_ROOT / ".github" / "pull_request_template.md"


def _load_validate_workflow() -> dict:
    return yaml.safe_load(_VALIDATE_WORKFLOW.read_text())


def test_validate_workflow_runs_work_sizing_floor_gate_from_pr_body():
    workflow = _load_validate_workflow()
    steps = workflow["jobs"]["validate"]["steps"]
    matches = [
        step
        for step in steps
        if step.get("name") == "Creator Engine validator — work-sizing floor PR-diff gate (G5)"
    ]

    assert len(matches) == 1
    step = matches[0]
    assert step.get("if") == "${{ github.event_name == 'pull_request' }}"

    run = step["run"]
    assert "GITHUB_EVENT_PATH" in run
    assert "pull_request" in run and "body" in run
    assert "len(values) != 1" in run
    assert 'allowed = ("tiny", "story", "feature", "epic")' in run
    assert "verify-work-sizing-floor" in run
    assert "--declared-work-class" in run
    assert "${declared_work_class}" in run
    assert "gh " not in run
    assert "api.github.com" not in run


def test_pull_request_template_declares_work_class_field():
    template = _PR_TEMPLATE.read_text()

    assert "- **Declared work class:**" in template
    assert "tiny / story / feature / epic" in template
