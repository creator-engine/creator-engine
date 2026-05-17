from pathlib import Path

from creator_engine_validator.checks.review_evidence_schema import (
    validate_review_evidence_record,
)


def valid_review_evidence() -> dict:
    return {
        "evidence_id": "example-review-evidence",
        "reviewed_artifact_refs": [
            "specs/001-v0-1-governance-substrate/spec.md",
        ],
        "reviewed_diff_or_commit_ref": "example/pre-merge-diff",
        "reviewer_identity_ref": "tenants/example-tenant/reviewer/identity-record.yml",
        "reviewer_role_category": "reviewer",
        "review_mode": "manual_human",
        "review_scope": "Example scope statement.",
        "mutation_classes_under_review": ["docs"],
        "prohibited_surfaces_checked": ["live_repository_settings"],
        "validation_evidence_refs": ["examples/well-formed"],
        "findings": "Example findings body.",
        "blocking_findings": [],
        "non_blocking_findings": [],
        "verdict": "no_blocking_findings",
        "recommended_follow_up": "",
        "evidence_timestamp": "source-controlled:examples/well-formed/review-evidence/example-review-evidence.yml",
        "non_ratification_statement": (
            "This review evidence is NOT Source ratification and does not "
            "authorize merge, deploy, branch deletion, branch protection "
            "mutation, or live repository-settings change."
        ),
    }


def test_review_evidence_accepts_well_formed_record(tmp_path: Path):
    record = valid_review_evidence()
    assert validate_review_evidence_record(record, tmp_path / "review-evidence.yml") == []


def test_review_evidence_missing_verdict_cites_fr001_and_contract(tmp_path: Path):
    record = valid_review_evidence()
    del record["verdict"]
    errors = validate_review_evidence_record(record, tmp_path / "review-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" for error in errors)
    assert all(error.contract == "docs/contracts/review-evidence.md" for error in errors)
    assert any("verdict" in error.message for error in errors)


def test_review_evidence_invalid_verdict_value_cites_fr001(tmp_path: Path):
    record = valid_review_evidence()
    record["verdict"] = "approved_for_merge"
    errors = validate_review_evidence_record(record, tmp_path / "review-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" and "verdict" in error.path for error in errors)
    assert any(error.contract == "docs/contracts/review-evidence.md" for error in errors)


def test_review_evidence_missing_non_ratification_statement_cites_fr001(tmp_path: Path):
    record = valid_review_evidence()
    del record["non_ratification_statement"]
    errors = validate_review_evidence_record(record, tmp_path / "review-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" for error in errors)
    assert any("non_ratification_statement" in error.message for error in errors)


def test_review_evidence_rejects_non_reviewer_role_category_via_schema(tmp_path: Path):
    record = valid_review_evidence()
    record["reviewer_role_category"] = "implementer"
    errors = validate_review_evidence_record(record, tmp_path / "review-evidence.yml")
    assert errors
    assert any("reviewer_role_category" in error.path for error in errors)


def test_review_evidence_rejects_empty_reviewed_artifact_refs(tmp_path: Path):
    record = valid_review_evidence()
    record["reviewed_artifact_refs"] = []
    errors = validate_review_evidence_record(record, tmp_path / "review-evidence.yml")
    assert errors
    assert any("reviewed_artifact_refs" in error.path for error in errors)


def test_review_evidence_rejects_unknown_extra_property(tmp_path: Path):
    record = valid_review_evidence()
    record["extra_unknown_field"] = "not allowed"
    errors = validate_review_evidence_record(record, tmp_path / "review-evidence.yml")
    assert errors
    assert any(error.code == "FR-001" for error in errors)


def test_review_evidence_accepts_iso_8601_timestamp(tmp_path: Path):
    record = valid_review_evidence()
    record["evidence_timestamp"] = "2026-05-17T12:34:56Z"
    assert validate_review_evidence_record(record, tmp_path / "review-evidence.yml") == []


def test_review_evidence_accepts_commit_ref_timestamp(tmp_path: Path):
    record = valid_review_evidence()
    record["evidence_timestamp"] = "commit:abc1234"
    assert validate_review_evidence_record(record, tmp_path / "review-evidence.yml") == []


def test_review_evidence_rejects_malformed_timestamp(tmp_path: Path):
    record = valid_review_evidence()
    record["evidence_timestamp"] = "yesterday"
    errors = validate_review_evidence_record(record, tmp_path / "review-evidence.yml")
    assert errors
    assert any("evidence_timestamp" in error.path for error in errors)


def test_review_evidence_structured_finding_requires_remediation(tmp_path: Path):
    record = valid_review_evidence()
    record["blocking_findings"] = [
        {
            "artifact_ref": "specs/example/spec.md",
            "rule_violated": "example rule",
            # recommended_remediation intentionally omitted
        }
    ]
    errors = validate_review_evidence_record(record, tmp_path / "review-evidence.yml")
    assert errors
    assert any("blocking_findings" in error.path for error in errors)
