from __future__ import annotations

import ast
import re
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from creator_engine_validator.forge import workflow_registry
from creator_engine_validator.forge.workflow_registry import (
    WORKFLOW_REGISTRY,
    WorkflowCatalogEntry,
    get_workflow,
    is_ratified,
    list_workflows,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "docs" / "contracts" / "workflow-catalog.md"


def _catalog_names() -> list[str]:
    text = CATALOG_PATH.read_text(encoding="utf-8")
    return re.findall(r"^### `([^`]+)`$", text, flags=re.MULTILINE)


def test_unknown_workflow_fails_closed_and_get_returns_none() -> None:
    assert is_ratified("unknown-workflow") is False
    assert get_workflow("unknown-workflow") is None


def test_default_seeded_workflows_are_unratified_and_fail_closed() -> None:
    workflows = list_workflows()

    assert workflows
    assert all(entry.ratified is False for entry in workflows)
    assert all(is_ratified(entry.name) is False for entry in workflows)


def test_list_workflows_and_get_workflow_return_catalog_entries() -> None:
    workflows = list_workflows()
    review_gate = get_workflow("review-gate")

    assert all(isinstance(entry, WorkflowCatalogEntry) for entry in workflows)
    assert [entry.name for entry in workflows] == list(WORKFLOW_REGISTRY)
    assert review_gate == workflows[0]
    assert review_gate is not None
    assert review_gate.purpose.startswith("route an authored change")
    assert review_gate.classification.startswith("mixed.")


def test_registry_names_match_workflow_catalog_document() -> None:
    assert [entry.name for entry in list_workflows()] == _catalog_names()


def test_registry_is_read_only_data() -> None:
    entry = get_workflow("review-gate")
    assert entry is not None

    with pytest.raises(FrozenInstanceError):
        entry.ratified = True

    with pytest.raises(TypeError):
        WORKFLOW_REGISTRY["review-gate"] = entry


def test_registry_module_has_no_execution_or_mutation_imports() -> None:
    forbidden_modules = {
        "creator_engine_validator.ce_cli",
        "creator_engine_validator.forge.broker",
        "creator_engine_validator.forge.cred_proxy",
        "creator_engine_validator.forge.cred_injection_proxy",
        "creator_engine_validator.forge.auto_merge",
        "creator_engine_validator.forge.automerge_policy",
        "subprocess",
        "requests",
        "urllib",
    }
    source = Path(workflow_registry.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)

    assert imported_modules.isdisjoint(forbidden_modules)
