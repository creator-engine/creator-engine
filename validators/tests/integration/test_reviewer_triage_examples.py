from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator.loader import load_yaml
from creator_engine_validator.schema import validate_with_schema
pytestmark = pytest.mark.slow


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "examples" / "reviewer-triage"
DECISION_SCHEMA = "schemas/reviewer-triage-decision.schema.yaml"
REGISTRY_SCHEMA = "schemas/reviewer-registry.schema.yaml"


@pytest.mark.parametrize(
    "name",
    [
        "eligible.yaml",
        "same-human-reject.yaml",
        "missing-access.yaml",
        "no-available-reviewer.yaml",
        "privileged-requires-source.yaml",
        "same-host-tier2-valid.yaml",
        "same-controller-tier1-reject.yaml",
        "unresolved-identity-reject.yaml",
        "uncontained-reject.yaml",
        "tier4-release-valid.yaml",
    ],
)
def test_reviewer_triage_examples_validate(name: str):
    path = EXAMPLES / name
    errors = validate_with_schema(
        load_yaml(path),
        DECISION_SCHEMA,
        path,
        code="VAL-REVIEWER-TRIAGE-SCHEMA",
        contract=DECISION_SCHEMA,
    )
    assert errors == []


def test_decision_schema_requires_non_authority_statement():
    data = load_yaml(EXAMPLES / "eligible.yaml")
    data.pop("non_authority_statement")
    errors = validate_with_schema(
        data,
        DECISION_SCHEMA,
        "eligible-without-non-authority.yaml",
        code="VAL-REVIEWER-TRIAGE-SCHEMA",
        contract=DECISION_SCHEMA,
    )
    assert errors


def test_reviewer_registry_schema_accepts_governed_registry_example():
    path = EXAMPLES / "reviewer-registry.yaml"
    errors = validate_with_schema(
        load_yaml(path),
        REGISTRY_SCHEMA,
        path,
        code="VAL-REVIEWER-REGISTRY-SCHEMA",
        contract=REGISTRY_SCHEMA,
    )
    assert errors == []
