from pathlib import Path

from creator_engine_validator.checks.implementer_evidence_schema import (
    validate_implementer_evidence_record,
)


def valid_implementer_evidence() -> dict:
    return {
        "evidence_id": "example-implementer-evidence",
        "implementation_subject": "Example implementation subject statement.",
        "authored_artifact_refs": [
            "schemas/implementer-evidence.schema.yaml",
        ],
        "allowed_path_boundary_refs": [
            "schemas/implementer-evidence.schema.yaml",
            "docs/contracts/implementer-evidence.md",
        ],
        "implementer_identity_ref": "tenants/example-tenant/implementer/identity-record.yml",
        "implementer_role_category": "implementer",
        "execution_mode": "manual_human",
        "implementation_scope": "Example scope statement.",
        "mutation_classes_executed": ["docs"],
        "prohibited_surfaces_acknowledged": ["live_repository_settings"],
        "validation_evidence_refs": ["examples/well-formed"],
        "test_evidence_refs": ["validators/tests"],
        "implementation_summary": "Example implementation summary body.",
        "deviations": [],
        "open_questions": [],
        "verdict": "implementation_complete",
        "recommended_follow_up": "",
        "evidence_timestamp": "source-controlled:examples/well-formed/implementer-evidence/example-implementer-evidence.yml",
        "non_ratification_statement": (
            "This implementer evidence is NOT Source ratification and does "
            "not authorize merge, deploy, branch deletion, branch protection "
            "mutation, live repository-settings change, "
            "provider/tool/model/host/account binding, tenant binding, or "
            "authority expansion."
        ),
    }


def test_implementer_evidence_accepts_well_formed_record(tmp_path: Path):
    record = valid_implementer_evidence()
    assert validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml") == []


def test_implementer_evidence_missing_verdict_cites_fr001_and_contract(tmp_path: Path):
    record = valid_implementer_evidence()
    del record["verdict"]
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" for error in errors)
    assert all(error.contract == "docs/contracts/implementer-evidence.md" for error in errors)
    assert any("verdict" in error.message for error in errors)


def test_implementer_evidence_invalid_verdict_value_cites_fr001(tmp_path: Path):
    record = valid_implementer_evidence()
    record["verdict"] = "approved_for_merge"
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" and "verdict" in error.path for error in errors)
    assert any(error.contract == "docs/contracts/implementer-evidence.md" for error in errors)


def test_implementer_evidence_missing_non_ratification_statement_cites_fr001(tmp_path: Path):
    record = valid_implementer_evidence()
    del record["non_ratification_statement"]
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" for error in errors)
    assert any("non_ratification_statement" in error.message for error in errors)


def test_implementer_evidence_rejects_non_implementer_role_category_via_schema(tmp_path: Path):
    record = valid_implementer_evidence()
    record["implementer_role_category"] = "architect"
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any("implementer_role_category" in error.path for error in errors)


def test_implementer_evidence_rejects_empty_authored_artifact_refs(tmp_path: Path):
    record = valid_implementer_evidence()
    record["authored_artifact_refs"] = []
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any("authored_artifact_refs" in error.path for error in errors)


def test_implementer_evidence_rejects_empty_allowed_path_boundary_refs(tmp_path: Path):
    record = valid_implementer_evidence()
    record["allowed_path_boundary_refs"] = []
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any("allowed_path_boundary_refs" in error.path for error in errors)


def test_implementer_evidence_rejects_empty_mutation_classes_executed(tmp_path: Path):
    record = valid_implementer_evidence()
    record["mutation_classes_executed"] = []
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any("mutation_classes_executed" in error.path for error in errors)


def test_implementer_evidence_rejects_empty_prohibited_surfaces_acknowledged(tmp_path: Path):
    record = valid_implementer_evidence()
    record["prohibited_surfaces_acknowledged"] = []
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any("prohibited_surfaces_acknowledged" in error.path for error in errors)


def test_implementer_evidence_rejects_unknown_extra_property(tmp_path: Path):
    record = valid_implementer_evidence()
    record["extra_unknown_field"] = "not allowed"
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" for error in errors)


def test_implementer_evidence_accepts_iso_8601_timestamp(tmp_path: Path):
    record = valid_implementer_evidence()
    record["evidence_timestamp"] = "2026-05-17T12:34:56Z"
    assert validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml") == []


def test_implementer_evidence_accepts_commit_ref_timestamp(tmp_path: Path):
    record = valid_implementer_evidence()
    record["evidence_timestamp"] = "commit:abc1234"
    assert validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml") == []


def test_implementer_evidence_rejects_malformed_timestamp(tmp_path: Path):
    record = valid_implementer_evidence()
    record["evidence_timestamp"] = "yesterday"
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any("evidence_timestamp" in error.path for error in errors)


def test_implementer_evidence_structured_deviation_requires_all_fields(tmp_path: Path):
    record = valid_implementer_evidence()
    record["deviations"] = [
        {
            "deviation_id": "boundary-clarification",
            "summary": "example summary",
            "justification": "example justification",
            # remediation_status intentionally omitted
        }
    ]
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any("deviations" in error.path for error in errors)


def test_implementer_evidence_accepts_populated_deviations(tmp_path: Path):
    record = valid_implementer_evidence()
    record["deviations"] = [
        {
            "deviation_id": "expected-fail-malformed-examples",
            "summary": "Malformed example CLI checks expected-fail.",
            "justification": "Documented expected-fail evidence; not a boundary expansion.",
            "remediation_status": "remediated_in_envelope",
        },
        {
            "deviation_id": "ambiguity-deferred",
            "summary": "Sibling cross-class evidence shape question deferred.",
            "justification": "Deferred to a separately Source-ratified follow-up envelope.",
            "remediation_status": "deferred_to_follow_up",
        },
    ]
    assert validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml") == []


def test_implementer_evidence_rejects_invalid_remediation_status(tmp_path: Path):
    record = valid_implementer_evidence()
    record["deviations"] = [
        {
            "deviation_id": "expected-fail-malformed-examples",
            "summary": "Malformed example CLI checks expected-fail.",
            "justification": "Documented expected-fail evidence.",
            "remediation_status": "silently_ratified",
        }
    ]
    errors = validate_implementer_evidence_record(record, tmp_path / "implementer-evidence.yml")
    assert errors
    assert any("remediation_status" in error.path for error in errors)
