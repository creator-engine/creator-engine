"""Workflow-lint: required-check workflows must trigger on ``merge_group`` (ce-ops#39).

GitHub's native merge queue runs required status checks on a synthetic
``merge_group`` event against a temporary ``gh-readonly-queue/...`` branch, NOT on
the PR head. If a *required* check's workflow does not list ``merge_group`` as a
trigger, the check never reports on the merge group and the queue STALLS forever
(the merge waits on a status that will never arrive).

These tests pin the load-bearing invariant for ce-ops#39: every workflow that
provides a *required* status-check context for the merge queue must carry the
``merge_group`` trigger with the only valid activity type, ``checks_requested``,
alongside its existing ``pull_request`` trigger. ``ce-ops-autoclose.yml`` is
deliberately excluded: it triggers on ``pull_request: closed`` (post-merge issue
closure), is not a required check, and has no role on the merge group.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOWS = _REPO_ROOT / ".github" / "workflows"

# Workflows that supply a *required* status-check context (and so must run on the
# merge group). Keyed by file; value is the required check job name(s) for the
# human reader — the test only needs the file to carry the trigger.
REQUIRED_CHECK_WORKFLOWS = ("validate.yml",)


def _load(name: str) -> dict:
    return yaml.safe_load((_WORKFLOWS / name).read_text())


def _on_block(doc: dict) -> dict:
    # PyYAML parses the bare key ``on:`` as the boolean True (YAML 1.1), so accept
    # either spelling rather than depending on how the file quotes the key.
    if "on" in doc:
        return doc["on"]
    return doc[True]


def test_validate_workflow_triggers_on_merge_group():
    """validate.yml (the 'Validate governance artifacts' required check) runs on merge_group."""
    on = _on_block(_load("validate.yml"))
    assert "merge_group" in on, (
        "validate.yml must trigger on merge_group or the merge queue stalls "
        "(required check never reports on gh-readonly-queue/*)"
    )
    mg = on["merge_group"]
    # The only valid merge_group activity type is checks_requested.
    assert isinstance(mg, dict) and mg.get("types") == ["checks_requested"], (
        "merge_group must declare types: [checks_requested] (the only valid activity type)"
    )


def test_validate_workflow_keeps_pull_request_trigger():
    """Adding merge_group must not drop the existing pull_request trigger (normal PRs)."""
    on = _on_block(_load("validate.yml"))
    assert "pull_request" in on, "validate.yml must still run on pull_request for normal PRs"
    # push-to-main is retained so post-merge main is still validated.
    assert "push" in on


def test_all_required_check_workflows_carry_merge_group():
    """Every required-check workflow carries the merge_group trigger (queue-stall guard)."""
    missing = []
    for name in REQUIRED_CHECK_WORKFLOWS:
        on = _on_block(_load(name))
        if "merge_group" not in on:
            missing.append(name)
    assert not missing, (
        f"required-check workflows missing merge_group trigger (queue would stall): {missing}"
    )
