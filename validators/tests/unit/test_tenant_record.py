"""Unit tests for tenant_record schema validation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.tenant_record import (
    CHECK_NAME,
    CODE_SCHEMA,
    run,
    validate_tenant_record,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PATH = REPO_ROOT / "examples/well-formed/tenant-records/acme.yaml"


def valid_tenant_record() -> dict:
    with EXAMPLE_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict)
    return data


def _messages(errors) -> str:
    return "\n".join(error.message for error in errors)


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs


def test_well_formed_example_passes():
    record = valid_tenant_record()
    assert validate_tenant_record(record, EXAMPLE_PATH) == []


def test_run_discovers_well_formed_example():
    result = run([EXAMPLE_PATH])
    assert result.ok, [error.format() for error in result.errors]


def test_missing_each_required_section_fails(tmp_path: Path):
    for section in (
        "identity",
        "credential",
        "confidentiality",
        "issue_venue",
        "fleet_allocation",
        "governance",
    ):
        record = valid_tenant_record()
        del record[section]
        errors = validate_tenant_record(record, tmp_path / f"missing-{section}.yaml")
        assert errors, section
        assert any(error.code == CODE_SCHEMA for error in errors)
        assert section in _messages(errors)


def test_raw_secret_value_in_ref_field_fails(tmp_path: Path):
    record = valid_tenant_record()
    record["identity"]["apps"][0]["private_key_ref"] = (
        "-----BEGIN PRIVATE KEY-----not-a-pointer-----END PRIVATE KEY-----"
    )
    errors = validate_tenant_record(record, tmp_path / "raw-secret.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_token_looking_secret_value_in_ref_field_fails(tmp_path: Path):
    record = valid_tenant_record()
    record["identity"]["apps"][0]["client_id_ref"] = "ghp_abcdefghijklmnopqrstuvwxyz123456"
    errors = validate_tenant_record(record, tmp_path / "raw-token.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_unknown_top_level_key_fails(tmp_path: Path):
    record = valid_tenant_record()
    record["unexpected"] = True
    errors = validate_tenant_record(record, tmp_path / "unknown-top.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_unknown_nested_key_fails(tmp_path: Path):
    record = valid_tenant_record()
    record["identity"]["apps"][0]["raw_private_key"] = "never"
    errors = validate_tenant_record(record, tmp_path / "unknown-nested.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_bad_top_level_enum_fails(tmp_path: Path):
    record = valid_tenant_record()
    record["status"] = "paused"
    errors = validate_tenant_record(record, tmp_path / "bad-status.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_bad_nested_enum_fails(tmp_path: Path):
    record = valid_tenant_record()
    record["identity"]["apps"][0]["custody_lane"] = "external"
    errors = validate_tenant_record(record, tmp_path / "bad-custody-lane.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_non_64_hex_ratification_ref_fails(tmp_path: Path):
    record = valid_tenant_record()
    record["governance"]["ratification_ref"] = "not-a-sha"
    errors = validate_tenant_record(record, tmp_path / "bad-ratification.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_policy_secret_ref_shape_passes(tmp_path: Path):
    record = valid_tenant_record()
    app = record["identity"]["apps"][0]
    app["app_id_ref"] = {
        "backend": "openbao",
        "mount": "tenant-acme",
        "path": "apps/forge",
        "field": "app_id",
        "version": 1,
        "purpose": "tenant app id",
        "owner_ref": "tenant:acme",
        "policy_sha": "c" * 64,
    }
    assert validate_tenant_record(record, tmp_path / "policy-secret-ref.yaml") == []


def test_wrong_kind_ignored_by_discovery(tmp_path: Path):
    record = deepcopy(valid_tenant_record())
    record["kind"] = "not-a-tenant-record"
    path = tmp_path / "tenant.yaml"
    path.write_text(yaml.safe_dump(record), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok
