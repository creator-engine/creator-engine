"""Unit tests for the RV1-022 ``state_version_record`` check (PCO v1 Gate 2)."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.state_version_record import (
    CHECK_NAME,
    CODE_SCHEMA,
    CODE_STALE,
    CURRENT_STATE_VERSION,
    run,
    validate_state_version_record,
)


def valid_state_version_record() -> dict:
    return {
        "kind": "state-version-record",
        "schema_version": "1",
        "state_namespace": "hermes-local",
        "state_version": CURRENT_STATE_VERSION,
        "migration_id": "none",
        "migration_status": "not-required",
        "record_timestamp": "2026-05-25T00:00:00Z",
    }


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs


def test_well_formed_state_version_record_passes(tmp_path: Path):
    errors = validate_state_version_record(valid_state_version_record(), tmp_path / "current.yaml")
    assert errors == [], [error.format() for error in errors]


def test_missing_required_field_fails(tmp_path: Path):
    record = valid_state_version_record()
    del record["migration_status"]

    errors = validate_state_version_record(record, tmp_path / "missing.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)
    assert all(
        error.contract == "docs/operations/STATE_BOUNDARY_PROTOCOL.md" for error in errors
    )


def test_unknown_field_is_refused(tmp_path: Path):
    record = valid_state_version_record()
    record["unexpected_field"] = "refused"

    errors = validate_state_version_record(record, tmp_path / "extra.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_invalid_migration_status_is_refused(tmp_path: Path):
    record = valid_state_version_record()
    record["migration_status"] = "completed"

    errors = validate_state_version_record(record, tmp_path / "status.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_stale_version_is_refused(tmp_path: Path):
    record = valid_state_version_record()
    record["state_version"] = CURRENT_STATE_VERSION - 1

    errors = validate_state_version_record(record, tmp_path / "stale.yaml")

    assert errors
    assert any(error.code == CODE_STALE for error in errors)


def test_future_version_is_refused(tmp_path: Path):
    record = valid_state_version_record()
    record["state_version"] = CURRENT_STATE_VERSION + 1

    errors = validate_state_version_record(record, tmp_path / "future.yaml")

    assert errors
    assert any(error.code == CODE_STALE for error in errors)


def test_non_integer_state_version_is_refused(tmp_path: Path):
    record = valid_state_version_record()
    record["state_version"] = "one"

    errors = validate_state_version_record(record, tmp_path / "noninteger.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_record_is_declarative_no_state_created(tmp_path: Path):
    validate_state_version_record(valid_state_version_record(), tmp_path / "x.yaml")
    assert not (tmp_path / ".hermes").exists()


def test_zero_records_passes(tmp_path: Path):
    assert run([tmp_path]).ok


def test_wrong_kind_is_ignored_by_discovery(tmp_path: Path):
    record = valid_state_version_record()
    record["kind"] = "not-a-state-version-record"
    (tmp_path / "stranger.yaml").write_text(yaml.safe_dump(record), encoding="utf-8")

    assert run([tmp_path]).ok


def test_tmp_file_is_skipped(tmp_path: Path):
    (tmp_path / "x.yaml.tmp.123").write_text(
        yaml.safe_dump({"kind": "state-version-record"}), encoding="utf-8"
    )

    assert run([tmp_path]).ok


def test_schemas_directory_excluded(tmp_path: Path):
    record = valid_state_version_record()
    record_path = tmp_path / "schemas" / "state-version-record.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    assert run([tmp_path]).ok
