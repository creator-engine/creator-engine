"""Unit tests for the ce_runtime_policy check (v3 G-1.0 plane-C substrate).

The check is the v3 translation of the v2 worker_container_policy check:
schema validation against ``schemas/runtime-policy.schema.yaml`` plus the
runtime-policy safety predicates (digest pin, forbidden mount, names-only
secrets, deny-by-default egress). Record-shape only — no live runtime.
"""

import copy
import hashlib
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
    CODE_SEMANTIC_DIGEST_MISMATCH,
    RuntimePolicyResolutionError,
    resolve_isolation_backend,
    run,
    runtime_policy_launch_stamp,
    runtime_policy_semantic_sha256,
    runtime_policy_source_sha256,
    validate_runtime_policy,
)

_POLICY_SHA = "a" * 64
_IMAGE_SHA = "sha256:" + "b" * 64


def valid_policy(role: str = "implementer") -> dict:
    record = {
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
    record["policy_sha"] = runtime_policy_semantic_sha256(record)
    return record


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
    assert CODE_SEMANTIC_DIGEST_MISMATCH in frs


def test_canonical_runtime_policy_has_exact_semantic_and_source_digests():
    path = Path("governance/policies/runtime/default-controller-v1.yaml")
    source = path.read_bytes()
    record = yaml.safe_load(source)
    assert runtime_policy_semantic_sha256(record) == "b26588442318a163d687e0e4fa10265ec2b1f41dccec5a9963df93b872281f55"
    assert runtime_policy_source_sha256(source) == "2cf79aefe9239a23cd21997f7bde13e030231a3aa30f0887be9797e24bccc31f"
    assert validate_runtime_policy(record, path) == []


def test_every_non_assertion_mutation_breaks_semantic_digest(tmp_path):
    record = valid_policy()
    for field, replacement in (
        ("policy_id", "other-policy-v1"),
        ("role", "verification"),
        ("grant_extensible", True),
    ):
        mutated = copy.deepcopy(record)
        mutated[field] = replacement
        assert CODE_SEMANTIC_DIGEST_MISMATCH in _codes(
            validate_runtime_policy(mutated, tmp_path / "default-controller-v1.yaml")
        )


def test_self_asserted_digest_replacement_cannot_forge_semantic_material(tmp_path):
    record = valid_policy()
    record["policy_id"] = "other-policy-v1"
    record["policy_sha"] = hashlib.sha256(record["policy_sha"].encode()).hexdigest()
    assert CODE_SEMANTIC_DIGEST_MISMATCH in _codes(
        validate_runtime_policy(record, tmp_path / "default-controller-v1.yaml")
    )


def test_reformat_is_byte_distinct_but_semantically_stable():
    path = Path("governance/policies/runtime/default-controller-v1.yaml")
    source = path.read_bytes()
    record = yaml.safe_load(source)
    reformatted = yaml.safe_dump(record, sort_keys=True).encode()
    assert runtime_policy_source_sha256(reformatted) != runtime_policy_source_sha256(source)
    assert runtime_policy_semantic_sha256(yaml.safe_load(reformatted)) == record["policy_sha"]


def test_canonical_policy_contains_names_only_subscription_cell_and_no_forbidden_material():
    text = Path("governance/policies/runtime/default-controller-v1.yaml").read_text()
    record = yaml.safe_load(text)
    assert record["secret_allowlist"] == ["codex-subscription-auth"]
    for forbidden in ("OPENAI_API_KEY", "auth.json", "docker.sock", "controller-key", "api.openai.com"):
        assert forbidden not in text


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


def test_well_formed_controller_policy_passes(tmp_path):
    record = valid_policy("controller")
    record["policy_id"] = "gvisor-controller-v1"
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []


def test_well_formed_docker_backend_passes(tmp_path):
    record = valid_policy()
    record["isolation_backend"] = "docker"
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []


def test_well_formed_openshell_backend_passes(tmp_path):
    record = valid_policy()
    record["isolation_backend"] = "openshell"
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []


def test_well_formed_local_noop_backend_passes(tmp_path):
    record = valid_policy()
    record["isolation_backend"] = "local-noop"
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []


def test_resolve_isolation_backend_aliases_cli_gvisor_to_policy_key():
    record = valid_policy()
    assert resolve_isolation_backend(record, explicit="gvisor") == "gvisor-proxy"


def test_resolve_isolation_backend_accepts_docker_key():
    record = valid_policy()
    record["isolation_backend"] = "docker"
    assert resolve_isolation_backend(record, explicit="docker") == "docker"


def test_resolve_isolation_backend_refuses_requested_policy_mismatch():
    record = valid_policy()
    record["isolation_backend"] = "openshell"
    try:
        resolve_isolation_backend(record, explicit="gvisor")
    except RuntimePolicyResolutionError as exc:
        assert "runtime policy declares 'openshell'" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("backend mismatch must fail closed")


def test_runtime_policy_launch_stamp_carries_policy_boundary_data(tmp_path):
    record = valid_policy()
    stamp = runtime_policy_launch_stamp(
        record,
        policy_ref=tmp_path / "runtime-policy.yaml",
        requested_backend="gvisor",
    )
    assert stamp["requested_backend"] == "gvisor"
    assert stamp["resolved_backend"] == "gvisor-proxy"
    assert stamp["policy_id"] == "gvisor-implementer-v1"
    assert stamp["image_ref"]["digest"].endswith("@sha256:" + "b" * 64)
    assert stamp["mount_manifest"] == record["mount_manifest"]
    assert stamp["egress_allowlist"] == record["egress_allowlist"]


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
    assert "docker" in backend_prop["enum"]
    assert "os-native" in backend_prop["enum"]
    assert "gvisor-proxy" in backend_prop["enum"]
    assert "local-noop" in backend_prop["enum"]
    assert "controller" in schema["properties"]["role"]["enum"]


def test_gvisor_proxy_pinned_record_still_validates(tmp_path):
    # req-4 back-compat: a fixture explicitly pinned to gvisor-proxy stays valid
    # (the default did NOT flip; gvisor-proxy remains in the enum).
    record = valid_policy()
    record["isolation_backend"] = "gvisor-proxy"
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []


def test_omitting_isolation_backend_validates_and_resolves_gvisor_proxy(tmp_path):
    # ce-ops#71 MINOR-A: a Draft 2020-12 validator does NOT inject schema defaults,
    # so isolation_backend is NOT in `required` — a record that OMITS it must
    # VALIDATE clean (the actual pre-#71 back-compat story), with the fail-closed
    # default supplied at RESOLUTION time (resolve_isolation_backend), not by the
    # schema. (Before this fix the required-list made an omitted field FAIL.)
    from creator_engine_validator import v3_installer

    record = valid_policy()
    del record["isolation_backend"]
    assert validate_runtime_policy(record, tmp_path / "policy.yml") == []
    assert v3_installer.resolve_isolation_backend() == "gvisor-proxy"


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
