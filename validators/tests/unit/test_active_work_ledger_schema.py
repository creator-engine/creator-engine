from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.active_work_ledger_schema import (
    CHECK_NAME,
    CODE_SCHEMA,
    run,
    validate_active_work_ledger_record,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def valid_claim_record() -> dict:
    return {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice0-author",
        "record_timestamp": "2026-05-20T03:30:30Z",
        "worktree_path": "/home/example/projects/creator-engine-worktrees/pco-slice0",
        "envelope_ref": ".hermes/envelopes/pco-slice0.md",
        "lease_seconds": 3600,
        "claimed_at": "2026-05-20T03:30:30Z",
        "last_heartbeat_at": "2026-05-20T03:30:30Z",
    }


def valid_heartbeat_record() -> dict:
    return {
        "kind": "active-work-ledger-record",
        "record_type": "heartbeat",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice0-author",
        "record_timestamp": "2026-05-20T03:31:00Z",
        "claim_ref": ".hermes/active-work-ledger/claims/hermes-primary/pco-slice0-author.yaml",
        "heartbeat_sequence": 1,
        "emitted_at": "2026-05-20T03:31:00Z",
    }


def valid_event_record() -> dict:
    return {
        "kind": "active-work-ledger-record",
        "record_type": "event",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice0-author",
        "record_timestamp": "2026-05-20T03:30:31Z",
        "event_kind": "claim_created",
        "event_id": "claim-created-001",
        "event_timestamp": "2026-05-20T03:30:31Z",
    }


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs


def test_well_formed_claim_record_passes(tmp_path: Path):
    record = valid_claim_record()
    assert validate_active_work_ledger_record(record, tmp_path / "claim.yaml") == []


def test_well_formed_heartbeat_record_passes(tmp_path: Path):
    record = valid_heartbeat_record()
    assert validate_active_work_ledger_record(record, tmp_path / "heartbeat.yaml") == []


def test_well_formed_event_record_passes(tmp_path: Path):
    record = valid_event_record()
    assert validate_active_work_ledger_record(record, tmp_path / "event.yaml") == []


def test_missing_required_field_fails(tmp_path: Path):
    record = valid_claim_record()
    del record["lane_id"]
    errors = validate_active_work_ledger_record(record, tmp_path / "claim.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)
    assert all(
        error.contract == "docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md"
        for error in errors
    )
    assert any("lane_id" in error.message for error in errors)


def test_bad_controller_id_pattern_fails(tmp_path: Path):
    record = valid_claim_record()
    record["controller_id"] = "Bad_ID"
    errors = validate_active_work_ledger_record(record, tmp_path / "claim.yaml")
    assert errors
    assert any("controller_id" in error.path for error in errors)


def test_bad_lane_id_pattern_fails(tmp_path: Path):
    record = valid_claim_record()
    record["lane_id"] = "Bad_Lane_ID"
    errors = validate_active_work_ledger_record(record, tmp_path / "claim.yaml")
    assert errors
    assert any("lane_id" in error.path for error in errors)


def test_invalid_timestamp_fails(tmp_path: Path):
    record = valid_claim_record()
    record["claimed_at"] = "yesterday"
    errors = validate_active_work_ledger_record(record, tmp_path / "claim.yaml")
    assert errors
    assert any("claimed_at" in error.path for error in errors)


def test_unknown_top_level_field_fails(tmp_path: Path):
    record = valid_claim_record()
    record["unexpected_stray_field"] = "not allowed"
    errors = validate_active_work_ledger_record(record, tmp_path / "claim.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_wrong_kind_field_is_ignored_by_discovery(tmp_path: Path):
    # A file whose kind is not active-work-ledger-record must not be
    # picked up by the discovery iterator at all (discriminator scoping).
    record = valid_claim_record()
    record["kind"] = "not-a-ledger-record"
    record_path = tmp_path / "stranger.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_tmp_file_is_skipped(tmp_path: Path):
    # An orphaned atomic-write temp file must be skipped without erroring.
    bad_record = {"kind": "active-work-ledger-record", "record_type": "claim"}
    tmp_file = tmp_path / "claim.yaml.tmp.12345.abcdef"
    tmp_file.write_text(yaml.safe_dump(bad_record), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_skeleton_scope_does_not_cross_validate(tmp_path: Path):
    # Two valid claims that collide on worktree_path under different
    # controller_ids must NOT produce an error from this check; the
    # collision check is later-slice scope (Slice 1 conflict validator).
    claim_a = valid_claim_record()
    claim_a["controller_id"] = "hermes-primary"
    claim_b = valid_claim_record()
    claim_b["controller_id"] = "nefarious-laptop-a"
    # both share worktree_path by virtue of using the same record fixture

    dir_a = tmp_path / "claims" / "hermes-primary"
    dir_b = tmp_path / "claims" / "nefarious-laptop-a"
    dir_a.mkdir(parents=True)
    dir_b.mkdir(parents=True)
    (dir_a / "pco-slice0-author.yaml").write_text(yaml.safe_dump(claim_a), encoding="utf-8")
    (dir_b / "pco-slice0-author.yaml").write_text(yaml.safe_dump(claim_b), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_run_emits_invalid_record_code_for_non_mapping(tmp_path: Path):
    # A YAML scalar at the top level cannot be picked up by discovery
    # (no `kind` field), so this also exercises the "not a ledger
    # record" skip path; if discovery ever changed to accept these,
    # the validator would emit the `active_work_ledger_invalid_record`
    # code, not PCO-001.
    record_path = tmp_path / "scalar.yaml"
    record_path.write_text("just-a-string\n", encoding="utf-8")
    result = run([tmp_path])
    assert result.ok


def test_event_record_requires_event_kind(tmp_path: Path):
    record = valid_event_record()
    del record["event_kind"]
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)
    # The oneOf discriminator surfaces the missing required field either
    # via the oneOf-clause message or as a structural error; both are
    # acceptable Slice 0 outcomes — the schema rejected the record.


def test_release_reason_constrained(tmp_path: Path):
    record = valid_claim_record()
    record["released_at"] = "2026-05-20T04:00:00Z"
    record["release_reason"] = "approved_for_merge"  # not in enum
    errors = validate_active_work_ledger_record(record, tmp_path / "claim.yaml")
    assert errors
    assert any("release_reason" in error.path for error in errors)


def test_slice_0_5_gate_opened_event_kind_accepted(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "2"
    record["event_kind"] = "gate_opened"
    record["event_id"] = "gate-opened-001"
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors == []


def test_slice_0_5_gate_closed_event_kind_accepted(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "2"
    record["event_kind"] = "gate_closed"
    record["event_id"] = "gate-closed-001"
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors == []


def test_slice_0_5_completion_report_emitted_event_kind_accepted(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "2"
    record["event_kind"] = "completion_report_emitted"
    record["event_id"] = "completion-report-emitted-001"
    record["details"] = {
        "summary": "report appended",
        "completion_report_ref": (
            ".hermes/research/example-archive/completion-report-20260520T070000Z.yaml"
        ),
    }
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors == []


def test_slice_0_5_gate_blocked_event_kind_accepted(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "2"
    record["event_kind"] = "gate_blocked"
    record["event_id"] = "gate-blocked-001"
    record["details"] = {
        "summary": "blocked",
        "completion_report_ref": (
            ".hermes/completion-reports/example-lane/20260520T091500Z.yaml"
        ),
    }
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors == []


def test_slice_0_v1_records_still_validate(tmp_path: Path):
    # The Slice 0.5 additive extension MUST NOT break Slice 0 v1 records.
    record = valid_event_record()
    # schema_version stays "1"; event_kind stays in the v1 set.
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors == []


def test_unknown_event_kind_still_rejected(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "2"
    record["event_kind"] = "completely_bogus_event_kind"
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors
    assert any("event_kind" in error.path for error in errors)


def test_bogus_schema_version_rejected(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "99"
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors
    assert any("schema_version" in error.path for error in errors)


def test_completion_report_ref_pattern_enforced(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "2"
    record["event_kind"] = "completion_report_emitted"
    record["event_id"] = "completion-report-emitted-bad-ref"
    record["details"] = {"completion_report_ref": "$$bad ref$$"}
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors
    assert any("completion_report_ref" in error.path for error in errors)


# Slice 2I-S v3 additive extension tests


def test_slice_2i_s_container_started_event_kind_accepted(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "3"
    record["event_kind"] = "container_started"
    record["event_id"] = "container-started-001"
    record["details"] = {
        "summary": "worker container started",
        "instance_id": "inst-pco-slice2i-001",
        "claim_id": "pco-slice2i-impl",
    }
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors == []


def test_slice_2i_s_container_stopped_event_kind_accepted(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "3"
    record["event_kind"] = "container_stopped"
    record["event_id"] = "container-stopped-001"
    record["details"] = {
        "summary": "worker container stopped",
        "instance_id": "inst-pco-slice2i-001",
        "claim_id": "pco-slice2i-impl",
        "exit_code": 0,
        "reason": "normal_release",
    }
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors == []


def test_slice_2i_s_container_force_reaped_event_kind_accepted(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "3"
    record["event_kind"] = "container_force_reaped"
    record["event_id"] = "container-force-reaped-001"
    record["details"] = {
        "summary": "container garbage collected",
        "instance_id": "inst-pco-slice2i-001",
        "claim_id": "pco-slice2i-impl",
        "reason": "force_reap",
        "elapsed_since_release_seconds": 120,
    }
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors == []


def test_slice_2i_s_v1_and_v2_records_still_validate(tmp_path: Path):
    # Slice 2I-S MUST NOT break Slice 0 v1 or Slice 0.5 v2 records.
    for version, kind in [
        ("1", "claim_created"),
        ("2", "gate_opened"),
        ("2", "completion_report_emitted"),
    ]:
        record = valid_event_record()
        record["schema_version"] = version
        record["event_kind"] = kind
        errors = validate_active_work_ledger_record(record, tmp_path / f"event-{version}-{kind}.yaml")
        assert errors == [], f"version={version} kind={kind} unexpectedly failed: {errors}"


def test_schema_version_3_accepted(tmp_path: Path):
    record = valid_claim_record()
    record["schema_version"] = "3"
    errors = validate_active_work_ledger_record(record, tmp_path / "claim.yaml")
    assert errors == []


def test_container_event_details_unknown_reason_rejected(tmp_path: Path):
    record = valid_event_record()
    record["schema_version"] = "3"
    record["event_kind"] = "container_stopped"
    record["event_id"] = "container-stopped-bad-reason"
    record["details"] = {
        "instance_id": "inst-pco-slice2i-001",
        "reason": "not_a_valid_reason",
    }
    errors = validate_active_work_ledger_record(record, tmp_path / "event.yaml")
    assert errors
    assert any("reason" in error.path for error in errors)
