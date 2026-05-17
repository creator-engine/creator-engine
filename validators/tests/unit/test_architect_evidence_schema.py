from pathlib import Path

from creator_engine_validator.checks.architect_evidence_schema import (
    validate_architect_evidence_record,
)


def valid_architect_evidence() -> dict:
    return {
        "evidence_id": "example-architect-evidence",
        "design_subject": "Example design subject statement.",
        "authored_artifact_refs": [
            "specs/001-v0-1-governance-substrate/spec.md",
        ],
        "architect_identity_ref": "tenants/example-tenant/architect/identity-record.yml",
        "architect_role_category": "architect",
        "authoring_mode": "manual_human",
        "design_scope": "Example scope statement.",
        "mutation_classes_proposed": ["docs"],
        "prohibited_surfaces_acknowledged": ["live_repository_settings"],
        "supporting_evidence_refs": ["examples/well-formed"],
        "recommendations": "Example recommendations body.",
        "decision_options": [],
        "open_questions": [],
        "verdict": "recommendation_complete",
        "recommended_follow_up": "",
        "evidence_timestamp": "source-controlled:examples/well-formed/architect-evidence/example-architect-evidence.yml",
        "non_ratification_statement": (
            "This architect evidence is NOT Source ratification and does not "
            "authorize merge, deploy, branch deletion, branch protection "
            "mutation, or live repository-settings change."
        ),
    }


def test_architect_evidence_accepts_well_formed_record(tmp_path: Path):
    record = valid_architect_evidence()
    assert validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml") == []


def test_architect_evidence_missing_verdict_cites_fr001_and_contract(tmp_path: Path):
    record = valid_architect_evidence()
    del record["verdict"]
    errors = validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" for error in errors)
    assert all(error.contract == "docs/contracts/architect-evidence.md" for error in errors)
    assert any("verdict" in error.message for error in errors)


def test_architect_evidence_invalid_verdict_value_cites_fr001(tmp_path: Path):
    record = valid_architect_evidence()
    record["verdict"] = "approved_for_merge"
    errors = validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" and "verdict" in error.path for error in errors)
    assert any(error.contract == "docs/contracts/architect-evidence.md" for error in errors)


def test_architect_evidence_missing_non_ratification_statement_cites_fr001(tmp_path: Path):
    record = valid_architect_evidence()
    del record["non_ratification_statement"]
    errors = validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" for error in errors)
    assert any("non_ratification_statement" in error.message for error in errors)


def test_architect_evidence_rejects_non_architect_role_category_via_schema(tmp_path: Path):
    record = valid_architect_evidence()
    record["architect_role_category"] = "implementer"
    errors = validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml")
    assert errors
    assert any("architect_role_category" in error.path for error in errors)


def test_architect_evidence_rejects_empty_authored_artifact_refs(tmp_path: Path):
    record = valid_architect_evidence()
    record["authored_artifact_refs"] = []
    errors = validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml")
    assert errors
    assert any("authored_artifact_refs" in error.path for error in errors)


def test_architect_evidence_rejects_empty_mutation_classes_proposed(tmp_path: Path):
    record = valid_architect_evidence()
    record["mutation_classes_proposed"] = []
    errors = validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml")
    assert errors
    assert any("mutation_classes_proposed" in error.path for error in errors)


def test_architect_evidence_rejects_empty_prohibited_surfaces_acknowledged(tmp_path: Path):
    record = valid_architect_evidence()
    record["prohibited_surfaces_acknowledged"] = []
    errors = validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml")
    assert errors
    assert any("prohibited_surfaces_acknowledged" in error.path for error in errors)


def test_architect_evidence_rejects_unknown_extra_property(tmp_path: Path):
    record = valid_architect_evidence()
    record["extra_unknown_field"] = "not allowed"
    errors = validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" for error in errors)


def test_architect_evidence_accepts_iso_8601_timestamp(tmp_path: Path):
    record = valid_architect_evidence()
    record["evidence_timestamp"] = "2026-05-17T12:34:56Z"
    assert validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml") == []


def test_architect_evidence_accepts_commit_ref_timestamp(tmp_path: Path):
    record = valid_architect_evidence()
    record["evidence_timestamp"] = "commit:abc1234"
    assert validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml") == []


def test_architect_evidence_rejects_malformed_timestamp(tmp_path: Path):
    record = valid_architect_evidence()
    record["evidence_timestamp"] = "yesterday"
    errors = validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml")
    assert errors
    assert any("evidence_timestamp" in error.path for error in errors)


def test_architect_evidence_structured_decision_option_requires_all_fields(tmp_path: Path):
    record = valid_architect_evidence()
    record["decision_options"] = [
        {
            "option_id": "option-a",
            "summary": "example summary",
            "tradeoffs": "example tradeoffs",
            # recommended_default intentionally omitted
        }
    ]
    errors = validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml")
    assert errors
    assert any("decision_options" in error.path for error in errors)


def test_architect_evidence_accepts_populated_decision_options(tmp_path: Path):
    record = valid_architect_evidence()
    record["decision_options"] = [
        {
            "option_id": "option-a",
            "summary": "Adopt the conservative shape.",
            "tradeoffs": "Preserves Phase 1 rigor.",
            "recommended_default": True,
        },
        {
            "option_id": "option-b",
            "summary": "Defer to a unified evidence schema later.",
            "tradeoffs": "Heavier schema-class amendment scope.",
            "recommended_default": False,
        },
    ]
    assert validate_architect_evidence_record(record, tmp_path / "architect-evidence.yml") == []
