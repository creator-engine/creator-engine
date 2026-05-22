"""Unit tests for the PCO Slice 2.5 ``controller_key_schema`` check."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.controller_key_schema import (
    CHECK_NAME,
    CODE_SCHEMA,
    run,
    validate_controller_key_record,
)


VALID_PUBLIC_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def valid_controller_key_record() -> dict:
    return {
        "kind": "controller-key-record",
        "record_type": "controller_key",
        "schema_version": "1",
        "tenant_id": "dogfood",
        "controller_id": "hermes-primary",
        "key_algorithm": "ed25519",
        "public_key": {
            "encoding": "base64url-no-padding",
            "value": VALID_PUBLIC_KEY,
        },
        "issued_at": "2026-05-22T00:00:00Z",
        "issued_by": "source-controlled:tenants/dogfood/identity.yaml",
        "key_custody_mode": "per_host",
        "status": "active",
    }


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs


def test_well_formed_controller_key_record_passes(tmp_path: Path):
    errors = validate_controller_key_record(
        valid_controller_key_record(), tmp_path / "hermes-primary.key.yaml"
    )
    assert errors == []


def test_missing_required_field_fails(tmp_path: Path):
    record = valid_controller_key_record()
    del record["controller_id"]

    errors = validate_controller_key_record(record, tmp_path / "missing.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)
    assert all(error.contract == "docs/operations/CONTROLLER_IDENTITY_PROTOCOL.md" for error in errors)


def test_bad_controller_id_pattern_fails(tmp_path: Path):
    record = valid_controller_key_record()
    record["controller_id"] = "Bad_ID"

    errors = validate_controller_key_record(record, tmp_path / "bad-controller.yaml")

    assert errors
    assert any("controller_id" in error.path for error in errors)


def test_invalid_base64url_public_key_fails(tmp_path: Path):
    record = valid_controller_key_record()
    record["public_key"]["value"] = "not+base64url/padding="

    errors = validate_controller_key_record(record, tmp_path / "bad-key.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA and "base64url" in error.message for error in errors)


def test_public_key_must_decode_to_32_bytes(tmp_path: Path):
    record = valid_controller_key_record()
    record["public_key"]["value"] = "AAA"

    errors = validate_controller_key_record(record, tmp_path / "short-key.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA and "32 bytes" in error.message for error in errors)


def test_private_key_material_is_rejected(tmp_path: Path):
    record = valid_controller_key_record()
    record["private_key"] = "fixture-private-key-material-is-not-allowed"

    errors = validate_controller_key_record(record, tmp_path / "secret.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA and "private/secret material" in error.message for error in errors)


def test_revoked_status_requires_revoked_at(tmp_path: Path):
    record = valid_controller_key_record()
    record["status"] = "revoked"

    errors = validate_controller_key_record(record, tmp_path / "revoked.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA and "revoked_at" in error.message for error in errors)


def test_non_per_host_custody_mode_fails(tmp_path: Path):
    record = valid_controller_key_record()
    record["key_custody_mode"] = "per_developer_tenant"

    errors = validate_controller_key_record(record, tmp_path / "wrong-custody.yaml")

    assert errors
    assert any("key_custody_mode" in error.path for error in errors)


def test_zero_controller_key_records_passes(tmp_path: Path):
    result = run([tmp_path])
    assert result.ok


def test_wrong_kind_field_is_ignored_by_discovery(tmp_path: Path):
    record = valid_controller_key_record()
    record["kind"] = "not-controller-key-record"
    record_path = tmp_path / "stranger.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])

    assert result.ok, f"unexpected errors: {[error.format() for error in result.errors]}"


def test_tmp_file_is_skipped(tmp_path: Path):
    bad_record = {"kind": "controller-key-record", "record_type": "controller_key"}
    record_path = tmp_path / "hermes-primary.key.yaml.tmp.12345"
    record_path.write_text(yaml.safe_dump(bad_record), encoding="utf-8")

    result = run([tmp_path])

    assert result.ok, f"unexpected errors: {[error.format() for error in result.errors]}"


def test_schemas_directory_excluded_from_discovery(tmp_path: Path):
    record = valid_controller_key_record()
    record_path = tmp_path / "schemas" / "controller-key.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])

    assert result.ok


def test_well_formed_record_under_tenant_controller_path_passes(tmp_path: Path):
    record = valid_controller_key_record()
    record_path = tmp_path / "tenants" / "dogfood" / "controllers" / "hermes-primary.key.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])

    assert result.ok, f"unexpected errors: {[error.format() for error in result.errors]}"
