"""Unit tests for the RV1-020 ``controller_runtime_contract`` check (PCO v1 Gate 2)."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.controller_runtime_contract import (
    CHECK_NAME,
    CODE_AUTHORITY,
    CODE_CONTAINMENT,
    CODE_SCHEMA,
    CODE_SECRET,
    run,
    validate_controller_runtime_contract_record,
)


def valid_controller_runtime_contract() -> dict:
    return {
        "kind": "controller-runtime-contract",
        "schema_version": "1",
        "role": "controller",
        "controller_seat": {
            "authority_locality": "host-local",
            "seat": "controller",
        },
        "harness": {"name": "claude-code"},
        "authority_boundary": {
            "in_seat_harnesses": ["hermes", "claude-code", "codex"],
            "seam_harnesses": ["openclaw"],
            "unauthorized_authorities": ["hosted-service", "saas", "github-connector"],
        },
        "state_boundary": {
            "state_root": ".hermes/",
            "durable_account_authority": "none",
            "provider_authority": "none",
        },
        "record_timestamp": "2026-05-25T00:00:00Z",
    }


CONTAINED_FORBIDDEN_SURFACES = [
    "host-home",
    "host-tmux-socket",
    "host-ssh-agent",
    "host-git-push",
    "acp-host-transport",
    "raw-host-tui",
    "docker-socket",
    "podman-socket",
    "containerd-socket",
    "openbao-root-token",
    "ce-root-v1-private-key",
    "github-app-private-key",
]


def valid_contained_controller_runtime_contract() -> dict:
    record = valid_controller_runtime_contract()
    record["controller_seat"]["authority_locality"] = "contained"
    record["controller_seat"]["containment"] = {
        "isolation_backend": "gvisor-proxy",
        "forbidden_surfaces": list(CONTAINED_FORBIDDEN_SURFACES),
        "credential_handles": {
            "max_auth": "max-auth-via-setup-token",
            "ce_root_v1": "ce-root-v1-via-openbao",
            "ce_root_v1_signing": "ce-root-v1-signing-request",
            "github_app": "github-app-installation-token",
        },
    }
    record["state_boundary"]["state_root"] = ".ce/state/"
    return record


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs
    assert CODE_CONTAINMENT in checks[CHECK_NAME].frs


def test_well_formed_controller_runtime_contract_passes(tmp_path: Path):
    errors = validate_controller_runtime_contract_record(
        valid_controller_runtime_contract(), tmp_path / "minimal.yaml"
    )
    assert errors == [], [error.format() for error in errors]


def test_missing_required_field_fails(tmp_path: Path):
    record = valid_controller_runtime_contract()
    del record["authority_boundary"]

    errors = validate_controller_runtime_contract_record(record, tmp_path / "missing.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)
    assert all(
        error.contract == "docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md"
        for error in errors
    )


def test_controller_role_must_be_controller(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record["role"] = "worker"

    errors = validate_controller_runtime_contract_record(record, tmp_path / "role.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA and "/role" in error.path for error in errors)


def test_unknown_field_is_refused(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record["unexpected_field"] = "refused"

    errors = validate_controller_runtime_contract_record(record, tmp_path / "extra.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_controller_seat_refuses_hosted_service(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record["controller_seat"]["authority_locality"] = "hosted-service"

    errors = validate_controller_runtime_contract_record(record, tmp_path / "seat.yaml")

    assert errors
    assert any("authority_locality" in error.path for error in errors)


def test_contained_controller_runtime_contract_passes(tmp_path: Path):
    errors = validate_controller_runtime_contract_record(
        valid_contained_controller_runtime_contract(), tmp_path / "contained.yaml"
    )
    assert errors == [], [error.format() for error in errors]


def test_contained_controller_requires_ce_state_root(tmp_path: Path):
    record = valid_contained_controller_runtime_contract()
    record["state_boundary"]["state_root"] = ".hermes/"

    errors = validate_controller_runtime_contract_record(record, tmp_path / "state-root.yaml")

    assert errors
    assert any(error.code == CODE_CONTAINMENT for error in errors)


def test_contained_controller_requires_containment_object(tmp_path: Path):
    record = valid_contained_controller_runtime_contract()
    del record["controller_seat"]["containment"]

    errors = validate_controller_runtime_contract_record(record, tmp_path / "containment.yaml")

    assert errors
    assert any(error.code == CODE_CONTAINMENT for error in errors)


def test_contained_controller_requires_forbidden_surface_floor(tmp_path: Path):
    record = valid_contained_controller_runtime_contract()
    record["controller_seat"]["containment"]["forbidden_surfaces"].remove("host-git-push")

    errors = validate_controller_runtime_contract_record(record, tmp_path / "surface.yaml")

    assert errors
    assert any(
        error.code == CODE_CONTAINMENT and "host-git-push" in error.message
        for error in errors
    )


def test_contained_request_handle_names_are_not_secret_values(tmp_path: Path):
    record = valid_contained_controller_runtime_contract()

    errors = validate_controller_runtime_contract_record(record, tmp_path / "handles.yaml")

    assert not [error for error in errors if error.code == CODE_SECRET]


def test_hosted_authority_in_seat_is_refused(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record["authority_boundary"]["in_seat_harnesses"] = [
        "hermes",
        "claude-code",
        "codex",
        "github-connector",
    ]

    errors = validate_controller_runtime_contract_record(record, tmp_path / "misclass.yaml")

    assert errors
    assert any(error.code == CODE_AUTHORITY for error in errors)


def test_missing_in_seat_harness_is_refused(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record["authority_boundary"]["in_seat_harnesses"] = ["hermes", "claude-code"]

    errors = validate_controller_runtime_contract_record(record, tmp_path / "missing-in.yaml")

    assert errors
    assert any(error.code == CODE_AUTHORITY for error in errors)


def test_openclaw_must_be_seam_not_in_seat(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record["authority_boundary"]["in_seat_harnesses"] = [
        "hermes",
        "claude-code",
        "codex",
        "openclaw",
    ]
    record["authority_boundary"]["seam_harnesses"] = []

    errors = validate_controller_runtime_contract_record(record, tmp_path / "openclaw.yaml")

    assert errors
    assert any(error.code == CODE_AUTHORITY for error in errors)


def test_hosted_authority_must_be_unauthorized(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record["authority_boundary"]["unauthorized_authorities"] = ["saas", "github-connector"]

    errors = validate_controller_runtime_contract_record(record, tmp_path / "unauth.yaml")

    assert errors
    assert any(error.code == CODE_AUTHORITY for error in errors)


def test_secret_value_field_is_refused(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record["description"] = "rotate model_api_key sk-ABCDEFGHIJKLMNOPQRSTUVWX0123456789"

    errors = validate_controller_runtime_contract_record(record, tmp_path / "secret.yaml")

    assert errors
    assert any(error.code == CODE_SECRET for error in errors)


def test_secret_bearing_key_name_is_refused(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record["controller_seat"]["api_key"] = "should-not-be-here"

    errors = validate_controller_runtime_contract_record(record, tmp_path / "secret-key.yaml")

    assert errors
    assert any(error.code in {CODE_SECRET, CODE_SCHEMA} for error in errors)


def test_record_does_not_mutate_runtime_state(tmp_path: Path):
    # Declarative validation must not create .hermes/ runtime state.
    validate_controller_runtime_contract_record(valid_controller_runtime_contract(), tmp_path / "x.yaml")
    assert not (tmp_path / ".hermes").exists()


def test_zero_records_passes(tmp_path: Path):
    assert run([tmp_path]).ok


def test_wrong_kind_is_ignored_by_discovery(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record["kind"] = "not-a-controller-runtime-contract"
    (tmp_path / "stranger.yaml").write_text(yaml.safe_dump(record), encoding="utf-8")

    assert run([tmp_path]).ok


def test_tmp_file_is_skipped(tmp_path: Path):
    record = {"kind": "controller-runtime-contract"}
    (tmp_path / "x.yaml.tmp.123").write_text(yaml.safe_dump(record), encoding="utf-8")

    assert run([tmp_path]).ok


def test_schemas_directory_excluded(tmp_path: Path):
    record = valid_controller_runtime_contract()
    record_path = tmp_path / "schemas" / "controller-runtime-contract.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    assert run([tmp_path]).ok
