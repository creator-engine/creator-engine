from pathlib import Path

from creator_engine_validator.checks.definition_of_ready import validate_definition_of_ready
from creator_engine_validator.checks.duplicate_spec_id import find_duplicate_spec_ids
from creator_engine_validator.checks.sidecar_conformance import validate_sidecar


def test_spec_sidecar_schema_accepts_well_formed_example():
    result = validate_sidecar(Path("examples/well-formed/spec.creator-engine.yml"))
    assert result.ok


def test_spec_sidecar_missing_acceptance_cites_fr009_and_contract():
    result = validate_sidecar(Path("examples/malformed/spec.creator-engine.missing-acceptance.yml"))
    assert any(error.code == "FR-009" for error in result.errors)
    assert any(error.contract == "docs/contracts/spec-wrapper-sidecar.md" for error in result.errors)


def test_definition_of_ready_missing_acceptance_cites_fr013():
    data = {
        "status": "ready",
        "scope": "Scope exists.",
        "verification": {"method": "validator", "evidence_refs": ["evidence"]},
    }
    errors = validate_definition_of_ready(Path("fixture.yml"), data)
    assert any(error.code == "FR-013" and "acceptance_criteria" in error.path for error in errors)
    assert all(error.contract == "docs/contracts/definition-of-ready.md" for error in errors)


def test_duplicate_spec_id_cites_fr027a():
    errors = find_duplicate_spec_ids([Path("examples/malformed/duplicate-spec-id")])
    assert any(error.code == "FR-027a" for error in errors)
    assert any(error.contract == "docs/contracts/spec-wrapper-sidecar.md" for error in errors)
