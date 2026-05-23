"""Unit tests for Side-Effect Ledger substrate checks (PCO-055..PCO-063)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.side_effect_ledger import (
    CHECK_NAME,
    CODE_COMPLETION_REPORT_BINDING,
    CODE_EFFECT_ID_UNIQUE,
    CODE_ENUMS,
    CODE_INTEGRATION_QUEUE_BINDING,
    CODE_LEDGER_BINDING,
    CODE_PANE_BINDING,
    CODE_REDACTION_SAFE,
    CODE_SCHEMA,
    CODE_STRICT_AND_TMP_SKIP,
    run,
    validate_side_effect_ledger_record,
)


def _write(path: Path, record: dict | str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(record, str):
        path.write_text(record, encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    return path


def valid_claim_record() -> dict:
    return {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice4-impl",
        "record_timestamp": "source-controlled:claims/hermes-primary/pco-slice4-impl.yaml",
        "worktree_path": "/worktrees/pco-slice4-impl",
        "envelope_ref": ".hermes/envelopes/pco-slice4.md",
        "lease_seconds": 3600,
        "claimed_at": "source-controlled:claims/hermes-primary/pco-slice4-impl.yaml",
        "last_heartbeat_at": "source-controlled:claims/hermes-primary/pco-slice4-impl.yaml",
    }


def valid_pane_record() -> dict:
    return {
        "kind": "pane-registry-record",
        "record_type": "pane_identity",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice4-impl",
        "claim_ref": "claims/hermes-primary/pco-slice4-impl.yaml",
        "host_id": "workstation-a",
        "pane_id": "pane-pco-slice4-impl-001",
        "role": "implementer",
        "status": "active",
        "record_timestamp": "2026-05-23T12:02:00Z",
        "registered_at": "2026-05-23T12:00:00Z",
        "last_seen_at": "source-controlled:panes/active-implementer.yaml",
        "visibility": "operator_visible",
        "terminal": {"kind": "tmux", "session_id": "ce-pco", "window_id": "slice4", "pane_id": "1"},
    }


def valid_completion_report() -> dict:
    return {
        "kind": "completion-report",
        "schema_version": "1",
        "gate_class": "A",
        "envelope_ref": "envelopes/pco-slice4.md",
        "envelope_sha256": "0" * 64,
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice4-impl",
        "gate_opened_at": "2026-05-23T12:00:00Z",
        "gate_closed_at": "2026-05-23T12:20:00Z",
        "outcome": "completed",
        "summary": "Substrate validation completed.",
        "recommended_immediate_next_step": {
            "description": "Return to Source.",
            "rationale": "Gate completed.",
            "next_action_kind": "source_ratifiable_prompt",
        },
        "exact_next_source_prompt": {
            "status": "none",
            "prompt_ref": None,
            "prompt_sha256": None,
            "absence_rationale": "No follow-up prompt required.",
        },
        "terminal_packet_sections_present": {
            "summary": True,
            "verification": True,
            "files_changed": True,
            "next_step": True,
        },
    }


def valid_side_effect_record() -> dict:
    return {
        "kind": "side-effect-ledger-record",
        "record_type": "side_effect",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice4-impl",
        "claim_ref": "claims/hermes-primary/pco-slice4-impl.yaml",
        "effect_id": "effect-tracked-file-change-001",
        "effect_kind": "tracked_file_change",
        "effect_status": "succeeded",
        "occurred_at": "2026-05-23T12:10:00Z",
        "record_timestamp": "2026-05-23T12:11:00Z",
        "summary": "Created a schema file.",
        "actor_role": "implementer",
        "subject_ref": "schemas/side-effect-ledger.schema.yaml",
        "evidence_refs": ["git diff -- schemas/side-effect-ledger.schema.yaml"],
        "redactions": ["No secret material recorded."],
        "details": {"path_count": 1},
    }


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    for code in (
        CODE_SCHEMA,
        CODE_LEDGER_BINDING,
        CODE_EFFECT_ID_UNIQUE,
        CODE_ENUMS,
        CODE_REDACTION_SAFE,
        CODE_PANE_BINDING,
        CODE_COMPLETION_REPORT_BINDING,
        CODE_INTEGRATION_QUEUE_BINDING,
        CODE_STRICT_AND_TMP_SKIP,
    ):
        assert code in checks[CHECK_NAME].frs


def test_well_formed_record_passes_schema_and_local_predicates(tmp_path: Path):
    assert validate_side_effect_ledger_record(valid_side_effect_record(), tmp_path / "effect.yaml") == []


def test_missing_required_field_fails_pco_055(tmp_path: Path):
    record = valid_side_effect_record()
    del record["summary"]
    errors = validate_side_effect_ledger_record(record, tmp_path / "effect.yaml")
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_invalid_effect_kind_and_status_fail_pco_058(tmp_path: Path):
    record = valid_side_effect_record()
    record["effect_kind"] = "git"
    record["effect_status"] = "done"
    errors = validate_side_effect_ledger_record(record, tmp_path / "effect.yaml")
    assert any(error.code == CODE_ENUMS for error in errors)


def test_unknown_top_level_field_fails_pco_063(tmp_path: Path):
    record = valid_side_effect_record()
    record["unexpected"] = "refused"
    errors = validate_side_effect_ledger_record(record, tmp_path / "effect.yaml")
    assert any(error.code == CODE_STRICT_AND_TMP_SKIP for error in errors)


def test_secret_bearing_payload_fails_pco_059(tmp_path: Path):
    record = valid_side_effect_record()
    record["details"] = {"api_token": "sk-secret-value"}
    errors = validate_side_effect_ledger_record(record, tmp_path / "effect.yaml")
    assert any(error.code == CODE_REDACTION_SAFE for error in errors)


def test_ledger_record_must_bind_to_matching_claim_pco_056(tmp_path: Path):
    _write(tmp_path / "side-effect-ledger" / "effect.yaml", valid_side_effect_record())
    result = run([tmp_path])
    assert not result.ok
    assert any(error.code == CODE_LEDGER_BINDING for error in result.errors)


def test_matching_claim_passes_pco_056(tmp_path: Path):
    _write(tmp_path / "claims" / "hermes-primary" / "pco-slice4-impl.yaml", valid_claim_record())
    _write(tmp_path / "side-effect-ledger" / "effect.yaml", valid_side_effect_record())
    result = run([tmp_path])
    assert result.ok, [error.format() for error in result.errors]


def test_effect_id_unique_within_controller_lane_utc_day_pco_057(tmp_path: Path):
    _write(tmp_path / "claims" / "hermes-primary" / "pco-slice4-impl.yaml", valid_claim_record())
    first = valid_side_effect_record()
    second = valid_side_effect_record()
    second["occurred_at"] = "2026-05-23T23:59:59Z"
    _write(tmp_path / "side-effect-ledger" / "effect-a.yaml", first)
    _write(tmp_path / "side-effect-ledger" / "effect-b.yaml", second)
    result = run([tmp_path])
    assert not result.ok
    assert any(error.code == CODE_EFFECT_ID_UNIQUE for error in result.errors)


def test_same_effect_id_on_different_utc_day_passes_pco_057(tmp_path: Path):
    _write(tmp_path / "claims" / "hermes-primary" / "pco-slice4-impl.yaml", valid_claim_record())
    first = valid_side_effect_record()
    second = valid_side_effect_record()
    second["occurred_at"] = "2026-05-24T00:00:00Z"
    _write(tmp_path / "side-effect-ledger" / "effect-a.yaml", first)
    _write(tmp_path / "side-effect-ledger" / "effect-b.yaml", second)
    result = run([tmp_path])
    assert result.ok, [error.format() for error in result.errors]


def test_pane_ref_must_match_claim_context_pco_060(tmp_path: Path):
    _write(tmp_path / "claims" / "hermes-primary" / "pco-slice4-impl.yaml", valid_claim_record())
    pane = valid_pane_record()
    pane["lane_id"] = "pco-other-lane"
    _write(tmp_path / "panes" / "active-implementer.yaml", pane)
    record = valid_side_effect_record()
    record["pane_ref"] = "panes/active-implementer.yaml"
    _write(tmp_path / "side-effect-ledger" / "effect.yaml", record)
    result = run([tmp_path])
    assert not result.ok
    assert any(error.code == CODE_PANE_BINDING for error in result.errors)


def test_completion_report_sha_must_match_referenced_file_pco_061(tmp_path: Path):
    _write(tmp_path / "claims" / "hermes-primary" / "pco-slice4-impl.yaml", valid_claim_record())
    report_path = _write(tmp_path / "completion-reports" / "report.yaml", valid_completion_report())
    record = valid_side_effect_record()
    record["completion_report_ref"] = "completion-reports/report.yaml"
    record["completion_report_sha256"] = hashlib.sha256(b"not the report").hexdigest()
    _write(tmp_path / "side-effect-ledger" / "effect.yaml", record)
    assert report_path.is_file()
    result = run([tmp_path])
    assert not result.ok
    assert any(error.code == CODE_COMPLETION_REPORT_BINDING for error in result.errors)


def test_integration_queue_ref_is_deferred_before_slice_6_pco_062(tmp_path: Path):
    _write(tmp_path / "claims" / "hermes-primary" / "pco-slice4-impl.yaml", valid_claim_record())
    record = valid_side_effect_record()
    record["integration_queue_ref"] = "integration-queue/future-entry.yaml"
    _write(tmp_path / "side-effect-ledger" / "effect.yaml", record)
    result = run([tmp_path])
    assert result.ok
    assert any(warning.code == CODE_INTEGRATION_QUEUE_BINDING for warning in result.warnings)


def test_tmp_artifacts_are_skipped_pco_063(tmp_path: Path):
    _write(tmp_path / "claims" / "hermes-primary" / "pco-slice4-impl.yaml", valid_claim_record())
    _write(tmp_path / "side-effect-ledger" / "effect.yaml", valid_side_effect_record())
    tmp_record = valid_side_effect_record()
    del tmp_record["summary"]
    _write(tmp_path / "side-effect-ledger" / "effect.tmp.yaml", tmp_record)
    result = run([tmp_path])
    assert result.ok, [error.format() for error in result.errors]
