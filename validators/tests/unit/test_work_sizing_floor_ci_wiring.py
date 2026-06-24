"""Workflow/template guard for work-sizing floor CI wiring."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VALIDATE_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "validate.yml"
_PR_TEMPLATE = _REPO_ROOT / ".github" / "pull_request_template.md"


def _load_validate_workflow() -> dict:
    return yaml.safe_load(_VALIDATE_WORKFLOW.read_text())


def _validate_step(name: str) -> dict:
    workflow = _load_validate_workflow()
    steps = workflow["jobs"]["validate"]["steps"]
    matches = [step for step in steps if step.get("name") == name]
    assert len(matches) == 1
    return matches[0]


def _fetch_with_shallow_retry_source() -> str:
    run = _validate_step("Resolve live comparison base")["run"]
    match = re.search(
        r"^fetch_with_shallow_retry\(\) \{\n.*?^\}$",
        run,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None
    return match.group(0)


def test_validate_workflow_resolves_live_comparison_base_from_git():
    step = _validate_step("Resolve live comparison base")

    assert step.get("id") == "live-base"
    assert step.get("if") == "${{ github.event_name == 'pull_request' || github.event_name == 'merge_group' }}"

    run = step["run"]
    assert "GITHUB_BASE_REF" in run
    assert "GITHUB_EVENT_PATH" in run
    assert "pull_request" in run
    assert "merge_group" in run
    assert "base_ref" in run
    assert "git fetch" in run
    assert "refs/remotes/origin/${base_ref}" in run
    assert "git merge-base" in run
    assert "origin/${base_ref}" in run
    assert "comparison_base=${comparison_base}" in run

    workflow_text = _VALIDATE_WORKFLOW.read_text()
    assert "github.event.pull_request.base.sha" not in workflow_text
    assert "PR_BASE_SHA" not in workflow_text


def test_fetch_with_shallow_retry_preserves_non_race_fetch_failure_status(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text(
        """#!/usr/bin/env bash
if [[ "$1" == "fetch" ]]; then
  echo "fatal: authentication failed" >&2
  exit 42
fi
exit 99
""",
        encoding="utf-8",
    )
    fake_git.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    script = (
        f"set -euo pipefail\n{_fetch_with_shallow_retry_source()}\n"
        "fetch_with_shallow_retry --no-tags origin +refs/heads/main:refs/remotes/origin/main\n"
    )

    completed = subprocess.run(
        ["bash", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 42
    assert "fatal: authentication failed" in completed.stderr
    assert "shallow metadata race" not in completed.stderr


def test_validate_workflow_runs_work_sizing_floor_gate_from_pr_body():
    step = _validate_step("Creator Engine validator — work-sizing floor PR-diff gate (G5)")
    assert step.get("if") == "${{ github.event_name == 'pull_request' }}"

    run = step["run"]
    assert 'comparison_base="${{ steps.live-base.outputs.comparison_base }}"' in run
    assert "GITHUB_EVENT_PATH" in run
    assert "pull_request" in run and "body" in run
    assert "len(values) != 1" in run
    assert 'allowed = ("tiny", "story", "feature", "epic")' in run
    assert "verify-work-sizing-floor" in run
    assert '--base "${comparison_base}"' in run
    assert "--declared-work-class" in run
    assert "${declared_work_class}" in run
    assert "gh " not in run
    assert "api.github.com" not in run


def test_validate_workflow_runs_path_manifest_gate_from_live_base_and_head_ref():
    step = _validate_step("Creator Engine validator — path-manifest PR-diff gate (G-ii)")
    assert step.get("if") == "${{ github.event_name == 'pull_request' }}"

    run = step["run"]
    assert 'comparison_base="${{ steps.live-base.outputs.comparison_base }}"' in run
    assert "GITHUB_HEAD_REF" in run
    assert "verify-path-manifest" in run
    assert '--base "${comparison_base}"' in run
    assert "--manifest-dir .ce/pr-manifests" in run
    assert '--head-ref "${GITHUB_HEAD_REF}"' in run
    assert "--require-carrier" in run
    assert "github.event.pull_request.base.sha" not in run
    assert "PR_BASE_SHA" not in run


def test_pull_request_template_declares_work_class_field():
    template = _PR_TEMPLATE.read_text()

    assert "- **Declared work class:**" in template
    assert "tiny / story / feature / epic" in template
