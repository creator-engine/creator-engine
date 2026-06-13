"""Unit tests for the ce_runtime_policy check (v3 G-1.0 plane-C substrate).

The check is the v3 translation of the v2 worker_container_policy check:
schema validation against ``schemas/runtime-policy.schema.yaml`` plus the
runtime-policy safety predicates (digest pin, forbidden mount, names-only
secrets, deny-by-default egress). Record-shape only — no live runtime.
"""

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.ce_runtime_policy import (
    CHECK_NAME,
    CODE_EGRESS_NOT_DENY_BY_DEFAULT,
    CODE_FORBIDDEN_MOUNT,
    CODE_IMAGE_NAME_CREDENTIAL,
    CODE_IMAGE_NOT_DIGEST_PINNED,
    CODE_RW_WITHOUT_JUSTIFICATION,
    CODE_SCHEMA,
    CODE_SECRET_NAMES_ONLY,
    run,
    validate_runtime_policy,
)

_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def valid_policy(role: str = "implementer") -> dict:
    return {
        "kind": "runtime-policy-record",
        "record_type": "runtime_policy",
        "schema_version": "1",
        "policy_id": "gvisor-implementer-v1",
        "policy_sha": _POLICY_SHA,
        "role": role,
        "isolation_backend": "gvisor-proxy",
        "image_ref": {
            "name": "registry.example/creator-engine/implementer",
            "sha": _IMAGE_SHA,
        },
        "mount_manifest": [
            {
                "path": "/runtime/worktree",
                "mode": "rw",
                "write_justification": "allocated worktree for this seat",
            },
            {"path": "governance", "mode": "ro"},
        ],
        "egress_allowlist": [
            {"host": "model-provider.example", "protocol": "https", "assurance": ["l4"]},
            {
                "host": "package-registry.example",
                "protocol": "https",
                "assurance": ["l7"],
                "tls_terminated": True,
            },
        ],
        "secret_allowlist": ["model-provider-key"],
        "grant_extensible": False,
        "grant_authority": "controller",
    }


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = checks[CHECK_NAME].frs
    assert CODE_SCHEMA in frs
    assert CODE_IMAGE_NOT_DIGEST_PINNED in frs
    assert CODE_FORBIDDEN_MOUNT in frs
    assert CODE_SECRET_NAMES_ONLY in frs
    assert CODE_EGRESS_NOT_DENY_BY_DEFAULT in frs


# ---------------------------------------------------------------------------
# Well-formed
# ---------------------------------------------------------------------------
def test_well_formed_implementer_policy_passes(tmp_path):
    assert validate_runtime_policy(valid_policy("implementer"), tmp_path / "policy.yml") == []


def test_well_formed_architect_research_policy_passes(tmp_path):
    record = valid_policy("architect_research")
    record["policy_id"] = "gvisor-architect-research-v1"
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []


def test_well_formed_verification_policy_no_egress_passes(tmp_path):
    record = valid_policy("verification")
    record["policy_id"] = "gvisor-verification-v1"
    record["egress_allowlist"] = []  # deny-by-default floor: no egress is valid
    record["secret_allowlist"] = []
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []


def test_well_formed_openshell_backend_passes(tmp_path):
    record = valid_policy()
    record["isolation_backend"] = "openshell"
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []


# ---------------------------------------------------------------------------
# ce-ops#71 Tranche 1 — the os-native backend is schema-valid, and the
# default-flip migration is GATED (req-4): omitting isolation_backend keeps the
# gvisor-proxy default, and gvisor-pinned records stay valid.
# ---------------------------------------------------------------------------
def test_well_formed_os_native_backend_passes(tmp_path):
    record = valid_policy()
    record["isolation_backend"] = "os-native"
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []


def test_default_flip_is_gated_schema_default_stays_gvisor_proxy():
    # req-4 GATE on the default-flip migration: adding os-native to the enum must
    # NOT flip the schema-declared default — records/answer-files that don't pin
    # the field keep gvisor-proxy, so no silent global flip breaks pinned fixtures.
    schema = yaml.safe_load(
        Path("schemas/runtime-policy.schema.yaml").read_text(encoding="utf-8")
    )
    backend_prop = schema["properties"]["isolation_backend"]
    assert backend_prop["default"] == "gvisor-proxy"
    assert "os-native" in backend_prop["enum"]
    assert "gvisor-proxy" in backend_prop["enum"]


def test_gvisor_proxy_pinned_record_still_validates(tmp_path):
    # req-4 back-compat: a fixture explicitly pinned to gvisor-proxy stays valid
    # (the default did NOT flip; gvisor-proxy remains in the enum).
    record = valid_policy()
    record["isolation_backend"] = "gvisor-proxy"
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []


# ---------------------------------------------------------------------------
# Schema violations (CODE_SCHEMA)
# ---------------------------------------------------------------------------
def test_missing_required_field_fails_schema(tmp_path):
    record = valid_policy()
    del record["role"]
    errors = validate_runtime_policy(record, tmp_path / "policy.yml")
    assert CODE_SCHEMA in _codes(errors)
    assert any("role" in e.message for e in errors)


def test_invalid_role_fails_schema(tmp_path):
    record = valid_policy()
    record["role"] = "reviewer"
    assert CODE_SCHEMA in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_invalid_isolation_backend_fails_schema(tmp_path):
    record = valid_policy()
    record["isolation_backend"] = "podman-rootless"  # v2 engine is NOT carried
    assert CODE_SCHEMA in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_unknown_top_level_field_fails_schema(tmp_path):
    record = valid_policy()
    record["unexpected_stray_field"] = "not allowed"
    assert CODE_SCHEMA in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


# ---------------------------------------------------------------------------
# Image digest pin
# ---------------------------------------------------------------------------
def test_image_without_sha_fails_not_digest_pinned(tmp_path):
    record = valid_policy()
    del record["image_ref"]["sha"]
    assert CODE_IMAGE_NOT_DIGEST_PINNED in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_image_with_non_sha256_sha_fails_not_digest_pinned(tmp_path):
    record = valid_policy()
    record["image_ref"]["sha"] = "latest"
    assert CODE_IMAGE_NOT_DIGEST_PINNED in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_image_name_with_userinfo_fails_credential(tmp_path):
    record = valid_policy()
    record["image_ref"]["name"] = "user:token@registry.example/creator-engine/implementer"
    assert CODE_IMAGE_NAME_CREDENTIAL in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


# ---------------------------------------------------------------------------
# Forbidden mounts (translate PCO-045)
# ---------------------------------------------------------------------------
def test_forbidden_home_mount_dollar_home_fails(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "$HOME/.ssh/id_rsa", "mode": "ro"}]
    assert CODE_FORBIDDEN_MOUNT in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_forbidden_home_mount_tilde_fails(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "~/.gnupg", "mode": "ro"}]
    assert CODE_FORBIDDEN_MOUNT in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_forbidden_docker_socket_fails(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "/var/run/docker.sock", "mode": "ro"}]
    assert CODE_FORBIDDEN_MOUNT in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_forbidden_podman_socket_fails(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "/run/podman/podman.sock", "mode": "ro"}]
    assert CODE_FORBIDDEN_MOUNT in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_forbidden_ssh_dir_absolute_path_fails(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "/home/agent/.ssh", "mode": "ro"}]
    assert CODE_FORBIDDEN_MOUNT in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_ro_mount_on_governance_path_passes(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "validators", "mode": "ro"}]
    errors = validate_runtime_policy(record, tmp_path / "policy.yml")
    assert CODE_FORBIDDEN_MOUNT not in _codes(errors)


# ---------------------------------------------------------------------------
# rw mount justification
# ---------------------------------------------------------------------------
def test_rw_mount_without_justification_fails(tmp_path):
    record = valid_policy()
    record["mount_manifest"] = [{"path": "/runtime/worktree", "mode": "rw"}]
    assert CODE_RW_WITHOUT_JUSTIFICATION in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


# ---------------------------------------------------------------------------
# Secret allowlist (names only; translate PCO-045)
# ---------------------------------------------------------------------------
def test_controller_key_secret_fails(tmp_path):
    record = valid_policy()
    record["secret_allowlist"] = ["controller-private-key"]
    assert CODE_SECRET_NAMES_ONLY in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_controller_key_variant_secret_fails(tmp_path):
    record = valid_policy()
    record["secret_allowlist"] = ["hermes-controller-key"]
    assert CODE_SECRET_NAMES_ONLY in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_private_key_named_secret_fails(tmp_path):
    record = valid_policy()
    record["secret_allowlist"] = ["id_ed25519"]
    assert CODE_SECRET_NAMES_ONLY in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_secret_that_is_a_path_fails(tmp_path):
    record = valid_policy()
    record["secret_allowlist"] = ["/run/secrets/model-provider-key"]
    assert CODE_SECRET_NAMES_ONLY in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_secret_keyfile_extension_fails(tmp_path):
    record = valid_policy()
    record["secret_allowlist"] = ["model-provider.pem"]
    assert CODE_SECRET_NAMES_ONLY in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_bare_secret_name_passes(tmp_path):
    record = valid_policy()
    record["secret_allowlist"] = ["model-provider-key", "per-task-scoped-token"]
    errors = validate_runtime_policy(record, tmp_path / "policy.yml")
    assert CODE_SECRET_NAMES_ONLY not in _codes(errors)


# ---------------------------------------------------------------------------
# Egress (deny-by-default)
# ---------------------------------------------------------------------------
def test_egress_rule_missing_host_fails(tmp_path):
    record = valid_policy()
    record["egress_allowlist"] = [{"port": 443, "assurance": ["l4"]}]
    errors = validate_runtime_policy(record, tmp_path / "policy.yml")
    # The schema also requires host; the predicate names the deny-by-default breach.
    assert CODE_EGRESS_NOT_DENY_BY_DEFAULT in _codes(errors)


def test_egress_l7_without_tls_terminated_fails(tmp_path):
    record = valid_policy()
    record["egress_allowlist"] = [{"host": "package-registry.example", "assurance": ["l7"]}]
    assert CODE_EGRESS_NOT_DENY_BY_DEFAULT in _codes(validate_runtime_policy(record, tmp_path / "policy.yml"))


def test_empty_egress_is_valid_no_egress(tmp_path):
    record = valid_policy()
    record["egress_allowlist"] = []
    errors = validate_runtime_policy(record, tmp_path / "policy.yml")
    assert CODE_EGRESS_NOT_DENY_BY_DEFAULT not in _codes(errors)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def test_wrong_kind_ignored_by_discovery(tmp_path):
    record = valid_policy()
    record["kind"] = "not-a-runtime-policy-record"
    (tmp_path / "policy.yml").write_text(yaml.safe_dump(record), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_tmp_file_skipped(tmp_path):
    bad = {"kind": "runtime-policy-record", "record_type": "runtime_policy"}
    tmp_file = tmp_path / "policy.yml.tmp.12345.abcdef"
    tmp_file.write_text(yaml.safe_dump(bad), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok


def test_run_over_well_formed_example_passes():
    result = run([Path("examples/well-formed/runtime-policy")])
    assert result.ok, [e.format() for e in result.errors]


# ---------------------------------------------------------------------------
# v3 G-4 — additive action-gate fields (action_class_allowlist + gate_mode_ladder)
# ---------------------------------------------------------------------------
def test_g4_legacy_policy_without_action_fields_still_validates():
    # A G-1.0 policy that omits the new fields remains valid (back-compatible).
    policy = valid_policy()
    assert "action_class_allowlist" not in policy
    assert _codes(validate_runtime_policy(policy, Path("x.yml"))) == set()


def test_g4_policy_with_action_fields_validates():
    policy = valid_policy()
    policy["action_class_allowlist"] = [{"op": "write", "mutation_class": "docs"}]
    policy["gate_mode_ladder"] = {
        "default_mode": "ask",
        "cells": [{"op": "write", "mutation_class": "code", "mode": "auto"}],
        "rules": [
            {"effect": "always_deny", "op": "vcs", "mutation_class": "deploy",
             "require_different_approver": True},
        ],
    }
    assert _codes(validate_runtime_policy(policy, Path("x.yml"))) == set()


def test_g4_bad_action_field_enums_fail_schema():
    bad_op = valid_policy()
    bad_op["action_class_allowlist"] = [{"op": "frobnicate", "mutation_class": "docs"}]
    assert CODE_SCHEMA in _codes(validate_runtime_policy(bad_op, Path("x.yml")))

    bad_mode = valid_policy()
    bad_mode["gate_mode_ladder"] = {"default_mode": "YOLO"}
    assert CODE_SCHEMA in _codes(validate_runtime_policy(bad_mode, Path("x.yml")))

    bad_effect = valid_policy()
    bad_effect["gate_mode_ladder"] = {"rules": [{"effect": "always_maybe"}]}
    assert CODE_SCHEMA in _codes(validate_runtime_policy(bad_effect, Path("x.yml")))
