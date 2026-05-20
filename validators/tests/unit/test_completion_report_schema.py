from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.completion_report_schema import (
    CHECK_NAME,
    CODE_SCHEMA,
    run,
    validate_completion_report_record,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def valid_class_a_record() -> dict:
    return {
        "kind": "completion-report",
        "schema_version": "1",
        "gate_class": "A",
        "envelope_ref": ".hermes/envelopes/source-ratify-example.md",
        "envelope_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "controller_id": "hermes-primary",
        "lane_id": "completion-report-substrate-author",
        "gate_opened_at": "2026-05-20T06:02:45Z",
        "gate_closed_at": "2026-05-20T07:00:00Z",
        "outcome": "completed",
        "summary": "Authored the Slice 0.5 substrate inside the allowed path manifest.",
        "recommended_immediate_next_step": {
            "description": "Open the commit/PR mechanics gate.",
            "rationale": "Authoring verification passed; mechanics is next.",
            "next_action_kind": "source_ratifiable_prompt",
        },
        "exact_next_source_prompt": {
            "kind": "present",
            "prompt_path": ".hermes/envelopes/source-ratify-next.md",
            "prompt_sha256": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
            "canonical_ratification_line": "Source ratifies the mechanics gate.",
        },
        "terminal_packet_sections_present": {
            "summary": True,
            "recommended_immediate_next_step": True,
            "exact_next_source_prompt_pointer_sha256": True,
        },
    }


def valid_class_c_merge_record() -> dict:
    record = valid_class_a_record()
    record["gate_class"] = "C-merge"
    record["merge_report"] = {
        "pr_number": 52,
        "pr_url_or_identifier": "https://github.com/example-org/creator-engine/pull/52",
        "merge_commit": "dab1ac9f5792b7439be1f0210d89bd558afbd53d",
        "head_ref": "feature/pco-slice0-active-work-ledger-20260520T031930Z",
        "head_sha": "bef8a7e70319fce48e68ebb021d0d213e3ee7fa0",
        "base_ref": "main",
        "base_sha": "184e88f",
        "merged_at": "2026-05-20T05:24:00Z",
        "merged_by_role": "controller",
        "merge_strategy": "squash",
        "validator_summary_ref": ".hermes/research/pco-slice0/validator-summary.json",
    }
    return record


def valid_class_d_record() -> dict:
    record = valid_class_a_record()
    record["gate_class"] = "D"
    record["interim_side_effect_note_ref"] = ".hermes/completion-reports/lane/note.md"
    record["interim_side_effect_note_sha256"] = (
        "5555555555555555555555555555555555555555555555555555555555555555"
    )
    record["mutation_descriptors"] = [
        {
            "target_class": "mcp.config",
            "target_identifier_redacted": "mcp:<redacted>",
            "change_summary": "Rotated redacted entry.",
        }
    ]
    return record


def valid_class_e_record() -> dict:
    record = valid_class_a_record()
    record["gate_class"] = "E"
    record["research_archive_path"] = ".hermes/research/example-architect/"
    record["evidence_index_path"] = ".hermes/research/example-architect/index.json"
    record["evidence_artifact_pointers"] = [
        ".hermes/research/example-architect/report.md"
    ]
    return record


def valid_class_f_record() -> dict:
    record = valid_class_a_record()
    record["gate_class"] = "F"
    record["outcome"] = "blocked"
    record["blocker_description"] = "Upstream substrate not ratified."
    record["resumption_pointer"] = {
        "kind": "present",
        "prompt_path": ".hermes/envelopes/source-ratify-resume.md",
        "prompt_sha256": "8888888888888888888888888888888888888888888888888888888888888888",
    }
    return record


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs


def test_well_formed_class_a_passes(tmp_path: Path):
    record = valid_class_a_record()
    assert validate_completion_report_record(record, tmp_path / "report.yaml") == []


def test_well_formed_class_c_merge_passes(tmp_path: Path):
    record = valid_class_c_merge_record()
    assert validate_completion_report_record(record, tmp_path / "report.yaml") == []


def test_well_formed_class_d_passes(tmp_path: Path):
    record = valid_class_d_record()
    assert validate_completion_report_record(record, tmp_path / "report.yaml") == []


def test_well_formed_class_e_passes(tmp_path: Path):
    record = valid_class_e_record()
    assert validate_completion_report_record(record, tmp_path / "report.yaml") == []


def test_well_formed_class_f_passes(tmp_path: Path):
    record = valid_class_f_record()
    assert validate_completion_report_record(record, tmp_path / "report.yaml") == []


def test_missing_envelope_sha256_fails(tmp_path: Path):
    record = valid_class_a_record()
    del record["envelope_sha256"]
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)
    assert any("envelope_sha256" in error.message for error in errors)
    assert all(
        error.contract == "docs/operations/COMPLETION_REPORT_PROTOCOL.md"
        for error in errors
    )


def test_envelope_sha256_bad_hex_fails(tmp_path: Path):
    record = valid_class_a_record()
    record["envelope_sha256"] = "not-a-real-sha"
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors
    assert any("envelope_sha256" in error.path for error in errors)


def test_bad_gate_class_fails(tmp_path: Path):
    record = valid_class_a_record()
    record["gate_class"] = "Z"
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_class_c_merge_missing_merge_report_fails(tmp_path: Path):
    record = valid_class_c_merge_record()
    del record["merge_report"]
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors


def test_class_d_missing_mutation_descriptors_fails(tmp_path: Path):
    record = valid_class_d_record()
    del record["mutation_descriptors"]
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors


def test_class_e_missing_evidence_pointers_fails(tmp_path: Path):
    record = valid_class_e_record()
    del record["evidence_artifact_pointers"]
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors


def test_class_f_blocked_outcome_requires_blocker(tmp_path: Path):
    record = valid_class_f_record()
    del record["blocker_description"]
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors


def test_class_f_aborted_outcome_allowed(tmp_path: Path):
    record = valid_class_f_record()
    record["outcome"] = "aborted"
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors == []


def test_class_f_completed_outcome_rejected(tmp_path: Path):
    record = valid_class_f_record()
    record["outcome"] = "completed"
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors


def test_exact_next_source_prompt_none_requires_rationale(tmp_path: Path):
    record = valid_class_e_record()
    record["exact_next_source_prompt"] = {"kind": "none"}
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors


def test_exact_next_source_prompt_none_with_rationale_passes(tmp_path: Path):
    record = valid_class_e_record()
    record["exact_next_source_prompt"] = {
        "kind": "none",
        "none_rationale": "source_paused_program",
    }
    record["recommended_immediate_next_step"]["next_action_kind"] = "no_next_gate"
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors == []


def test_exact_next_source_prompt_none_with_freeform_rationale_rejected(tmp_path: Path):
    record = valid_class_e_record()
    record["exact_next_source_prompt"] = {
        "kind": "none",
        "none_rationale": "i felt like stopping",
    }
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors


def test_unknown_top_level_field_fails(tmp_path: Path):
    record = valid_class_a_record()
    record["unexpected_stray_field"] = "not allowed"
    errors = validate_completion_report_record(record, tmp_path / "report.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_wrong_kind_field_is_ignored_by_discovery(tmp_path: Path):
    record = valid_class_a_record()
    record["kind"] = "not-a-completion-report"
    record_path = tmp_path / "stranger.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_tmp_file_is_skipped(tmp_path: Path):
    bad_record = {"kind": "completion-report", "schema_version": "1"}
    tmp_file = tmp_path / "report.yaml.tmp.12345.abcdef"
    tmp_file.write_text(yaml.safe_dump(bad_record), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok


def test_bundled_well_formed_examples_pass():
    examples_dir = REPO_ROOT / "examples" / "well-formed" / "completion-reports"
    result = run([examples_dir])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_bundled_malformed_examples_fail():
    malformed_dir = REPO_ROOT / "examples" / "malformed" / "completion-reports"
    # missing-envelope-sha256.yaml, blocked-without-blocker.yaml, none-without-rationale.yaml
    # fail CR-001. mismatched-sha.yaml is schema-valid but fails CR-002.
    for fname in (
        "missing-envelope-sha256.yaml",
        "blocked-without-blocker.yaml",
        "none-without-rationale.yaml",
    ):
        path = malformed_dir / fname
        result = run([path])
        assert not result.ok, f"{fname} unexpectedly passed CR-001"
        assert any(error.code == CODE_SCHEMA for error in result.errors)
