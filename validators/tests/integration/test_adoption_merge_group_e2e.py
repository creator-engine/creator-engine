"""Adoption workflow parity for non-CE-shaped fixture repositories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from creator_engine_validator import onboard_apply
from tests.unit.test_onboard_apply import (
    FakeAdoptionDriver,
    _adoption_apply,
    _brownfield_probe,
)

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[3]
CE_VALIDATE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "validate.yml"


def _workflow_triggers(workflow_yaml: str) -> dict[str, Any]:
    workflow = yaml.safe_load(workflow_yaml)
    if not isinstance(workflow, dict):
        return {}
    triggers = workflow.get("on", workflow.get(True, {}))
    return triggers if isinstance(triggers, dict) else {}


def _non_ce_shaped_probe() -> dict[str, Any]:
    probe = _brownfield_probe()
    probe["ci"] = {
        "workflows": [],
        "current_required_checks": [],
        "workflow_present": False,
    }
    return probe


def test_adoption_emits_merge_group_workflow_for_non_ce_shaped_repo(tmp_path):
    probe = _non_ce_shaped_probe()
    assert probe["ci"]["workflow_present"] is False
    assert probe["ci"]["workflows"] == []

    canonical_triggers = _workflow_triggers(CE_VALIDATE_WORKFLOW.read_text(encoding="utf-8"))
    assert canonical_triggers["merge_group"] == {"types": ["checks_requested"]}

    driver = FakeAdoptionDriver()
    summary = _adoption_apply(tmp_path, driver, probe=probe)

    assert summary["failed"] == 0
    assert summary["refused"] == 0
    workflow_artifact = next(
        artifact
        for artifact in driver.scaffold_artifacts or []
        if artifact["path"] == onboard_apply.CE_WORKFLOW_PATH
    )
    emitted = workflow_artifact["content"]
    emitted_triggers = _workflow_triggers(emitted)

    assert emitted_triggers["merge_group"] == {"types": ["checks_requested"]}
    assert emitted_triggers["merge_group"] == canonical_triggers["merge_group"]
    assert "CE_WORKFLOW_TEMPLATE" not in emitted
    assert "validators/" not in emitted
