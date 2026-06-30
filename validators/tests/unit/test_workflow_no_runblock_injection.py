"""Guard against GitHub Actions expressions inside shell ``run:`` blocks."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOWS = _REPO_ROOT / ".github" / "workflows"


def _github_expression_in(value: str) -> bool:
    start = value.find("${{")
    return start != -1 and value.find("}}", start + 3) != -1


def _run_block_expression_violations(workflow: dict[str, Any], workflow_name: str) -> list[str]:
    violations: list[str] = []
    jobs = workflow.get("jobs", {})
    if not isinstance(jobs, dict):
        return violations

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", [])
        if not isinstance(steps, list):
            continue
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict) or "run" not in step:
                continue
            run = step["run"]
            if not isinstance(run, str):
                continue
            if _github_expression_in(run):
                step_name = step.get("name") or f"step {index}"
                violations.append(f"{workflow_name}: jobs.{job_name}.steps[{index}] ({step_name})")
    return violations


def _load_workflow(path: Path) -> dict[str, Any]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), f"{path} must parse to a YAML mapping"
    return doc


def test_workflow_run_blocks_do_not_embed_github_expressions():
    violations: list[str] = []
    for path in sorted(_WORKFLOWS.glob("*.yml")):
        violations.extend(_run_block_expression_violations(_load_workflow(path), path.name))

    assert not violations, (
        "GitHub Actions expressions must be moved out of step run: bodies, "
        f"usually through env: indirection. Violations: {violations}"
    )


def test_run_block_expression_detection_rejects_interpolated_shell_body():
    workflow = yaml.safe_load(
        """
        name: fixture
        on: pull_request
        jobs:
          guard:
            runs-on: ubuntu-latest
            steps:
              - name: env expression is fine
                env:
                  BRANCH: ${{ github.head_ref }}
                if: ${{ always() }}
                with:
                  token: ${{ secrets.GITHUB_TOKEN }}
                run: |
                  printf '%s\\n' "${BRANCH}"
              - name: run expression is rejected
                run: |
                  echo "${{ github.event.pull_request.title }}"
        """
    )

    assert _run_block_expression_violations(workflow, "fixture.yml") == [
        "fixture.yml: jobs.guard.steps[2] (run expression is rejected)"
    ]
