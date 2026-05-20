import hashlib
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.completion_report_required_for_envelope import (
    CHECK_NAME,
    CODE_PAIRING,
    run,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def base_record() -> dict:
    return {
        "kind": "completion-report",
        "schema_version": "1",
        "gate_class": "A",
        "envelope_ref": ".hermes/envelopes/source-ratify-pairing-test.md",
        "envelope_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "controller_id": "hermes-primary",
        "lane_id": "pairing-test",
        "gate_opened_at": "2026-05-20T06:00:00Z",
        "gate_closed_at": "2026-05-20T06:30:00Z",
        "outcome": "completed",
        "summary": "Pairing test.",
        "recommended_immediate_next_step": {
            "description": "next step",
            "rationale": "follows from completion",
            "next_action_kind": "source_ratifiable_prompt",
        },
        "exact_next_source_prompt": {
            "kind": "present",
            "prompt_path": ".hermes/envelopes/source-ratify-next.md",
            "prompt_sha256": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
            "canonical_ratification_line": "Source ratifies the next gate.",
        },
        "terminal_packet_sections_present": {
            "summary": True,
            "recommended_immediate_next_step": True,
            "exact_next_source_prompt_pointer_sha256": True,
        },
    }


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_PAIRING in checks[CHECK_NAME].frs


def test_missing_envelope_file_is_skipped(tmp_path: Path):
    record = base_record()
    record_path = tmp_path / "report.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_matching_envelope_sha_passes(tmp_path: Path):
    envelope_path = tmp_path / "envelope.md"
    envelope_body = b"# fake envelope body\n"
    envelope_path.write_bytes(envelope_body)
    record = base_record()
    record["envelope_ref"] = "envelope.md"
    record["envelope_sha256"] = hashlib.sha256(envelope_body).hexdigest()
    record_path = tmp_path / "report.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    # Run with tmp_path as scanned path; the check resolves envelope_ref
    # against repo root candidates which include the report's parent.
    # To make the resolution deterministic for this fixture, also point
    # envelope_ref at the absolute path.
    record["envelope_ref"] = str(envelope_path)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_mismatched_envelope_sha_fails(tmp_path: Path):
    envelope_path = tmp_path / "envelope.md"
    envelope_path.write_bytes(b"# real envelope body\n")
    record = base_record()
    record["envelope_ref"] = str(envelope_path)
    record["envelope_sha256"] = "0" * 64  # cannot equal the real sha
    record_path = tmp_path / "report.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    result = run([tmp_path])
    assert not result.ok
    assert any(error.code == CODE_PAIRING for error in result.errors)
    assert any("envelope_sha256" in error.message or "envelope_sha256" in error.path for error in result.errors)


def test_two_completed_reports_for_same_envelope_fails(tmp_path: Path):
    record_a = base_record()
    record_b = base_record()
    record_b["lane_id"] = "pairing-test-b"
    (tmp_path / "report-a.yaml").write_text(yaml.safe_dump(record_a), encoding="utf-8")
    (tmp_path / "report-b.yaml").write_text(yaml.safe_dump(record_b), encoding="utf-8")
    result = run([tmp_path])
    assert not result.ok
    assert any(error.code == CODE_PAIRING for error in result.errors)


def test_partial_plus_completed_for_same_envelope_passes(tmp_path: Path):
    record_partial = base_record()
    record_partial["outcome"] = "partial"
    record_partial["lane_id"] = "pairing-test-partial"
    record_completed = base_record()
    (tmp_path / "report-partial.yaml").write_text(
        yaml.safe_dump(record_partial), encoding="utf-8"
    )
    (tmp_path / "report-completed.yaml").write_text(
        yaml.safe_dump(record_completed), encoding="utf-8"
    )
    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_bundled_well_formed_examples_pass():
    examples_dir = REPO_ROOT / "examples" / "well-formed" / "completion-reports"
    result = run([examples_dir])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_bundled_mismatched_sha_malformed_fails():
    fixture = (
        REPO_ROOT
        / "examples"
        / "malformed"
        / "completion-reports"
        / "mismatched-sha.yaml"
    )
    result = run([fixture])
    assert not result.ok
    assert any(error.code == CODE_PAIRING for error in result.errors)
