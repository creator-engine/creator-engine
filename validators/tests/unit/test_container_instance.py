"""Unit tests for container_instance check (PCO-041, PCO-043, PCO-044)."""

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.container_instance import (
    CHECK_NAME,
    CODE_SCHEMA,
    CODE_OUTLIVES_CLAIM,
    CODE_IMAGE_SHA_MISMATCH,
    run,
    validate_container_instance,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
_SHA256_HEX = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def valid_running_instance() -> dict:
    return {
        "kind": "container-instance-record",
        "record_type": "container_instance",
        "schema_version": "1",
        "instance_id": "inst-pco-slice2i-s-001",
        "policy_ref": {
            "policy_id": "podman-implementer-v1",
            "policy_sha": _SHA256_HEX,
            "image_sha": _IMAGE_SHA,
        },
        "image_sha": _IMAGE_SHA,
        "claim_id": "pco-slice2i-s-impl",
        "lease_id": "lease-slice2i-001",
        "started_at": "2026-05-22T05:33:05Z",
        "stopped_at": None,
        "exit_code": None,
        "mount_manifest_applied": [
            {"path": "/worktrees/my-feature", "mode": "rw", "source": "policy"},
            {"path": "governance", "mode": "ro", "source": "policy"},
        ],
        "secret_grants": [
            {
                "secret_name": "model-provider-key",
                "mode": "env",
                "broker_grant_id": "grant-abc-001",
                "granted_at": "2026-05-22T05:33:05Z",
                "revoked_at": None,
                "ttl_seconds": 3600,
            }
        ],
        "egress_allowlist_applied": [
            {"host": "api.anthropic.com", "protocol": "https"},
        ],
        "enforcement_primitive": "pasta",
        "policy_sha": _SHA256_HEX,
    }


def valid_stopped_instance() -> dict:
    record = valid_running_instance()
    record["instance_id"] = "inst-pco-slice2i-s-002"
    record["stopped_at"] = "2026-05-22T06:00:00Z"
    record["exit_code"] = 0
    return record


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs
    assert CODE_OUTLIVES_CLAIM in checks[CHECK_NAME].frs
    assert CODE_IMAGE_SHA_MISMATCH in checks[CHECK_NAME].frs


def test_well_formed_running_instance_passes(tmp_path):
    record = valid_running_instance()
    assert validate_container_instance(record, tmp_path / "instance.yaml") == []


def test_well_formed_stopped_instance_passes(tmp_path):
    record = valid_stopped_instance()
    assert validate_container_instance(record, tmp_path / "instance.yaml") == []


def test_missing_instance_id_fails_pco_041(tmp_path):
    record = valid_running_instance()
    del record["instance_id"]
    errors = validate_container_instance(record, tmp_path / "instance.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)
    assert any("instance_id" in e.message for e in errors)


def test_missing_policy_sha_fails_pco_041(tmp_path):
    record = valid_running_instance()
    del record["policy_sha"]
    errors = validate_container_instance(record, tmp_path / "instance.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)


def test_missing_policy_ref_image_sha_fails_pco_041(tmp_path):
    record = valid_running_instance()
    del record["policy_ref"]["image_sha"]
    errors = validate_container_instance(record, tmp_path / "instance.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)


def test_unknown_top_level_field_fails_pco_041(tmp_path):
    record = valid_running_instance()
    record["unexpected_stray_field"] = "not allowed"
    errors = validate_container_instance(record, tmp_path / "instance.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)


def test_secret_grant_with_secret_value_fails_pco_041(tmp_path):
    record = valid_running_instance()
    record["secret_grants"][0]["secret_value"] = "super-secret"
    errors = validate_container_instance(record, tmp_path / "instance.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)


def test_container_outlives_released_claim_fails_pco_043(tmp_path):
    record = valid_running_instance()
    record["claim_released_at"] = "2026-05-22T05:45:00Z"
    # stopped_at is still None → container is still running after claim released
    errors = validate_container_instance(record, tmp_path / "instance.yaml")
    assert errors
    codes = [e.code for e in errors]
    assert CODE_OUTLIVES_CLAIM in codes


def test_stopped_container_with_released_claim_passes_pco_043(tmp_path):
    record = valid_running_instance()
    record["claim_released_at"] = "2026-05-22T05:45:00Z"
    record["stopped_at"] = "2026-05-22T05:45:01Z"
    record["exit_code"] = 0
    errors = validate_container_instance(record, tmp_path / "instance.yaml")
    pco043 = [e for e in errors if e.code == CODE_OUTLIVES_CLAIM]
    assert pco043 == []


def test_running_instance_no_claim_released_at_passes_pco_043(tmp_path):
    record = valid_running_instance()
    # No claim_released_at means claim is still live → no PCO-043
    errors = validate_container_instance(record, tmp_path / "instance.yaml")
    pco043 = [e for e in errors if e.code == CODE_OUTLIVES_CLAIM]
    assert pco043 == []


def test_image_sha_mismatch_fails_pco_044(tmp_path):
    record = valid_running_instance()
    record["image_sha"] = "sha256:" + "c" * 64  # differs from policy_ref.image_sha
    errors = validate_container_instance(record, tmp_path / "instance.yaml")
    assert errors
    codes = [e.code for e in errors]
    assert CODE_IMAGE_SHA_MISMATCH in codes


def test_image_sha_matches_policy_passes_pco_044(tmp_path):
    record = valid_running_instance()
    # image_sha matches policy_ref.image_sha
    errors = validate_container_instance(record, tmp_path / "instance.yaml")
    pco044 = [e for e in errors if e.code == CODE_IMAGE_SHA_MISMATCH]
    assert pco044 == []


def test_wrong_kind_ignored_by_discovery(tmp_path):
    record = valid_running_instance()
    record["kind"] = "not-a-container-instance-record"
    record_path = tmp_path / "instance.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_tmp_file_skipped(tmp_path):
    bad = {"kind": "container-instance-record", "record_type": "container_instance"}
    tmp_file = tmp_path / "instance.yaml.tmp.12345.abcdef"
    tmp_file.write_text(yaml.safe_dump(bad), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok
