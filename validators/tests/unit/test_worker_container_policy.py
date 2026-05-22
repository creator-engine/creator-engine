"""Unit tests for worker_container_policy check (PCO-040, PCO-045)."""

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.worker_container_policy import (
    CHECK_NAME,
    CODE_SCHEMA,
    CODE_FORBIDDEN_MOUNT,
    run,
    validate_worker_container_policy,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
_SHA256_HEX = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def valid_policy(role: str = "implementer") -> dict:
    return {
        "kind": "worker-container-policy-record",
        "record_type": "worker_container_policy",
        "schema_version": "1",
        "policy_id": "podman-implementer-v1",
        "policy_sha": _SHA256_HEX,
        "role": role,
        "runtime_engine": "podman-rootless",
        "image_ref": {
            "name": "ghcr.io/creator-engine/implementer:latest",
            "sha": _IMAGE_SHA,
        },
        "mount_manifest": [
            {
                "path": "/worktrees/my-feature",
                "mode": "rw",
                "write_justification": "allocated worktree for this task",
            },
            {
                "path": "governance",
                "mode": "ro",
            },
        ],
        "egress_allowlist": [
            {"host": "api.anthropic.com", "protocol": "https"},
        ],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs
    assert CODE_FORBIDDEN_MOUNT in checks[CHECK_NAME].frs


def test_well_formed_implementer_policy_passes(tmp_path):
    record = valid_policy("implementer")
    assert validate_worker_container_policy(record, tmp_path / "policy.yaml") == []


def test_well_formed_architect_research_policy_passes(tmp_path):
    record = valid_policy("architect_research")
    record["policy_id"] = "podman-architect-research-v1"
    assert validate_worker_container_policy(record, tmp_path / "policy.yaml") == []


def test_well_formed_verification_policy_passes(tmp_path):
    record = valid_policy("verification")
    record["policy_id"] = "podman-verification-v1"
    record["egress_allowlist"] = []
    record["secret_allowlist"] = []
    assert validate_worker_container_policy(record, tmp_path / "policy.yaml") == []


def test_well_formed_docker_rootless_engine_passes(tmp_path):
    record = valid_policy()
    record["runtime_engine"] = "docker-rootless"
    assert validate_worker_container_policy(record, tmp_path / "policy.yaml") == []


def test_missing_required_field_fails_pco_040(tmp_path):
    record = valid_policy()
    del record["role"]
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)
    assert any("role" in e.message for e in errors)


def test_invalid_role_fails_pco_040(tmp_path):
    record = valid_policy()
    record["role"] = "reviewer"
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)


def test_invalid_runtime_engine_fails_pco_040(tmp_path):
    record = valid_policy()
    record["runtime_engine"] = "bare-docker"
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)


def test_unknown_top_level_field_fails_pco_040(tmp_path):
    record = valid_policy()
    record["unexpected_stray_field"] = "not allowed"
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)


def test_forbidden_home_mount_dollar_home_fails_pco_045(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "$HOME/.ssh/id_rsa", "mode": "ro"}]
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_FORBIDDEN_MOUNT for e in errors)


def test_forbidden_home_mount_tilde_fails_pco_045(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "~/.gnupg", "mode": "ro"}]
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_FORBIDDEN_MOUNT for e in errors)


def test_forbidden_docker_socket_fails_pco_045(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "/var/run/docker.sock", "mode": "ro"}]
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_FORBIDDEN_MOUNT for e in errors)


def test_forbidden_podman_socket_fails_pco_045(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "/run/podman/podman.sock", "mode": "ro"}]
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_FORBIDDEN_MOUNT for e in errors)


def test_forbidden_var_run_podman_socket_fails_pco_045(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "/var/run/podman/podman.sock", "mode": "ro"}]
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_FORBIDDEN_MOUNT for e in errors)


def test_forbidden_controller_key_in_secret_allowlist_fails_pco_045(tmp_path):
    record = valid_policy()
    record["secret_allowlist"] = ["controller-private-key"]
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_FORBIDDEN_MOUNT for e in errors)


def test_forbidden_controller_key_variant_in_secret_allowlist_fails_pco_045(tmp_path):
    record = valid_policy()
    record["secret_allowlist"] = ["hermes-controller-key"]
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    assert errors
    assert any(e.code == CODE_FORBIDDEN_MOUNT for e in errors)


def test_wrong_kind_ignored_by_discovery(tmp_path):
    record = valid_policy()
    record["kind"] = "not-a-worker-container-policy-record"
    record_path = tmp_path / "policy.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_tmp_file_skipped(tmp_path):
    bad = {"kind": "worker-container-policy-record", "record_type": "worker_container_policy"}
    tmp_file = tmp_path / "policy.yaml.tmp.12345.abcdef"
    tmp_file.write_text(yaml.safe_dump(bad), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok


def test_ro_mount_on_validators_path_passes_pco_045(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "validators", "mode": "ro"}]
    errors = validate_worker_container_policy(record, tmp_path / "policy.yaml")
    # PCO-045 only forbids rw on governance trees, not ro
    pco045 = [e for e in errors if e.code == CODE_FORBIDDEN_MOUNT]
    assert pco045 == []
