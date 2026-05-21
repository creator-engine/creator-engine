"""Unit tests for the PCO Slice 2A ``worktree_lease_schema`` check.

The check validates one Worktree Lease record at a time against
``schemas/worktree-lease.schema.yaml`` and emits ``PCO-020`` failures
that cite ``docs/operations/WORKTREE_LEASE_PROTOCOL.md``.

The check is record-level: it MUST NOT cross-check lease/lease or
lease/claim relationships (those are owned by
``active_work_ledger_conflicts``). It MUST tolerate orphaned
``*.tmp.*`` atomic-write artifacts the same way the Slice 0 schema
check does.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.worktree_lease_schema import (
    CHECK_NAME,
    CODE_SCHEMA,
    run,
    validate_worktree_lease_record,
)


def valid_lease_record() -> dict:
    return {
        "kind": "worktree-lease-record",
        "record_type": "worktree_lease",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice2a-author",
        "record_timestamp": "2026-05-21T03:08:08Z",
        "lease_id": "lease-pco-slice2a-001",
        "worktree_path": "/home/example/projects/creator-engine-worktrees/pco-slice2a",
        "acquired_at": "2026-05-21T03:08:08Z",
        "lease_seconds": 3600,
        "expires_at": "2026-05-21T04:08:08Z",
    }


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs


def test_well_formed_lease_record_passes(tmp_path: Path):
    record = valid_lease_record()
    assert validate_worktree_lease_record(record, tmp_path / "lease.yaml") == []


def test_well_formed_lease_with_optional_fields_passes(tmp_path: Path):
    record = valid_lease_record()
    record["pane_label"] = "implementer"
    record["branch"] = "pco-slice-2a-feature"
    record["envelope_ref"] = ".hermes/envelopes/pco-slice2a.md"
    record["note"] = "Optional human-readable hint for the operator."
    assert validate_worktree_lease_record(record, tmp_path / "lease.yaml") == []


def test_missing_required_field_fails(tmp_path: Path):
    for field in (
        "lease_id",
        "worktree_path",
        "acquired_at",
        "lease_seconds",
        "expires_at",
        "controller_id",
        "lane_id",
        "record_timestamp",
    ):
        record = valid_lease_record()
        del record[field]
        errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
        assert errors, f"expected schema error for missing {field!r}"
        assert any(error.code == CODE_SCHEMA for error in errors)
        assert all(
            error.contract == "docs/operations/WORKTREE_LEASE_PROTOCOL.md"
            for error in errors
        )


def test_bad_controller_id_pattern_fails(tmp_path: Path):
    record = valid_lease_record()
    record["controller_id"] = "Bad_ID"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("controller_id" in error.path for error in errors)


def test_bad_lane_id_pattern_fails(tmp_path: Path):
    record = valid_lease_record()
    record["lane_id"] = "Bad_Lane_ID"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("lane_id" in error.path for error in errors)


def test_lease_seconds_below_minimum_fails(tmp_path: Path):
    record = valid_lease_record()
    record["lease_seconds"] = 30
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("lease_seconds" in error.path for error in errors)


def test_lease_seconds_above_maximum_fails(tmp_path: Path):
    record = valid_lease_record()
    record["lease_seconds"] = 90000
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("lease_seconds" in error.path for error in errors)


def test_bad_lease_id_pattern_fails(tmp_path: Path):
    record = valid_lease_record()
    record["lease_id"] = "Bad Lease ID!"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("lease_id" in error.path for error in errors)


def test_invalid_expires_at_shape_fails(tmp_path: Path):
    record = valid_lease_record()
    record["expires_at"] = "soon"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("expires_at" in error.path for error in errors)


def test_invalid_acquired_at_shape_fails(tmp_path: Path):
    record = valid_lease_record()
    record["acquired_at"] = "yesterday"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("acquired_at" in error.path for error in errors)


def test_unknown_top_level_field_fails(tmp_path: Path):
    record = valid_lease_record()
    record["unexpected_stray_field"] = "not allowed"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_pane_label_enum_constrained(tmp_path: Path):
    record = valid_lease_record()
    record["pane_label"] = "some-tool-binding"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("pane_label" in error.path for error in errors)


def test_wrong_kind_field_is_ignored_by_discovery(tmp_path: Path):
    record = valid_lease_record()
    record["kind"] = "not-a-lease-record"
    record_path = tmp_path / "stranger.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_tmp_file_is_skipped(tmp_path: Path):
    # Orphaned atomic-write temp file must be skipped without erroring.
    bad_record = {"kind": "worktree-lease-record", "record_type": "worktree_lease"}
    tmp_file = tmp_path / "lease.yaml.tmp.12345.abcdef"
    tmp_file.write_text(yaml.safe_dump(bad_record), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_well_formed_lease_under_directory_passes(tmp_path: Path):
    record = valid_lease_record()
    record_path = tmp_path / "leases" / "hermes-primary" / "lease.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_schemas_directory_excluded_from_discovery(tmp_path: Path):
    # The validator MUST NOT pick up files under a ``schemas/`` path so
    # that the canonical schema itself does not self-validate.
    record = valid_lease_record()
    record_path = tmp_path / "schemas" / "lease.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok
