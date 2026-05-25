"""Unit tests for the RV1-021 ``state_boundary_contract`` check (PCO v1 Gate 2)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.state_boundary_contract import (
    CHECK_NAME,
    CODE_IGNORE,
    CODE_SCHEMA,
    CODE_SECRET,
    CODE_WRITE,
    run,
    validate_state_boundary_contract_record,
)


def valid_state_boundary_contract() -> dict:
    return {
        "kind": "state-boundary-contract",
        "schema_version": "1",
        "state_root": ".hermes/",
        "allowed_write_roots": [".hermes/"],
        "forbidden_write_roots": [
            "docs/",
            "specs/",
            "schemas/",
            "templates/",
            "validators/",
        ],
        "tracked_artifact_policy": "refuse",
        "secret_policy": {
            "mode": "names-and-references-only",
            "recorded_secret_names": ["GH_TOKEN", "ANTHROPIC_API_KEY"],
        },
        "state_root_gitignored": True,
        "record_timestamp": "2026-05-25T00:00:00Z",
    }


def _write_record(directory: Path, record: dict, name: str = "minimal.yaml") -> Path:
    path = directory / name
    path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    return path


def _git_repo(directory: Path, gitignore_lines: list[str]) -> None:
    subprocess.run(["git", "init", "-q"], cwd=directory, check=True)
    (directory / ".gitignore").write_text("\n".join(gitignore_lines) + "\n", encoding="utf-8")


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs


def test_well_formed_state_boundary_contract_passes(tmp_path: Path):
    errors = validate_state_boundary_contract_record(
        valid_state_boundary_contract(), tmp_path / "minimal.yaml"
    )
    assert errors == [], [error.format() for error in errors]


def test_missing_required_field_fails(tmp_path: Path):
    record = valid_state_boundary_contract()
    del record["forbidden_write_roots"]

    errors = validate_state_boundary_contract_record(record, tmp_path / "missing.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)
    assert all(
        error.contract == "docs/operations/STATE_BOUNDARY_PROTOCOL.md" for error in errors
    )


def test_unknown_field_is_refused(tmp_path: Path):
    record = valid_state_boundary_contract()
    record["unexpected_field"] = "refused"

    errors = validate_state_boundary_contract_record(record, tmp_path / "extra.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_tracked_write_root_is_refused(tmp_path: Path):
    record = valid_state_boundary_contract()
    record["allowed_write_roots"] = [".hermes/", "docs/governance/"]

    errors = validate_state_boundary_contract_record(record, tmp_path / "tracked.yaml")

    assert errors
    assert any(error.code == CODE_WRITE for error in errors)


def test_allowed_write_roots_must_be_hermes_only(tmp_path: Path):
    record = valid_state_boundary_contract()
    record["allowed_write_roots"] = ["build/"]

    errors = validate_state_boundary_contract_record(record, tmp_path / "other.yaml")

    assert errors
    assert any(error.code == CODE_WRITE for error in errors)


def test_forbidden_write_roots_must_cover_protected_surfaces(tmp_path: Path):
    record = valid_state_boundary_contract()
    record["forbidden_write_roots"] = ["docs/"]

    errors = validate_state_boundary_contract_record(record, tmp_path / "thin.yaml")

    assert errors
    assert any(error.code == CODE_WRITE for error in errors)


def test_tracked_artifact_policy_must_be_refuse(tmp_path: Path):
    record = valid_state_boundary_contract()
    record["tracked_artifact_policy"] = "allow"

    errors = validate_state_boundary_contract_record(record, tmp_path / "policy.yaml")

    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_secret_value_in_config_is_refused(tmp_path: Path):
    record = valid_state_boundary_contract()
    record["secret_policy"]["recorded_secret_names"] = [
        "GH_TOKEN",
        "ghp_EXAMPLE0123456789abcdefABCDEF012345",
    ]

    errors = validate_state_boundary_contract_record(record, tmp_path / "secret.yaml")

    assert errors
    assert any(error.code == CODE_SECRET for error in errors)


def test_declared_not_ignored_is_refused(tmp_path: Path):
    record = valid_state_boundary_contract()
    record["state_root_gitignored"] = False

    errors = validate_state_boundary_contract_record(record, tmp_path / "not-ignored.yaml")

    assert errors
    assert any(error.code == CODE_IGNORE for error in errors)


def test_live_git_reports_state_root_not_ignored(tmp_path: Path):
    _git_repo(tmp_path, ["build/"])  # .hermes/ is NOT ignored here
    record = valid_state_boundary_contract()  # declares gitignored true, but git disagrees
    _write_record(tmp_path, record)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_IGNORE for error in result.errors)


def test_live_git_reports_state_root_ignored_passes(tmp_path: Path):
    _git_repo(tmp_path, [".hermes/"])
    _write_record(tmp_path, valid_state_boundary_contract())

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_no_git_context_does_not_false_fail(tmp_path: Path):
    _write_record(tmp_path, valid_state_boundary_contract())

    # No .git here; the live ignore check must not raise or invent an error.
    result = run([tmp_path])

    assert all(error.code != CODE_IGNORE for error in result.errors), [
        error.format() for error in result.errors
    ]


def test_record_is_read_only_no_hermes_created(tmp_path: Path):
    _write_record(tmp_path, valid_state_boundary_contract())
    run([tmp_path])
    assert not (tmp_path / ".hermes").exists()


def test_zero_records_passes(tmp_path: Path):
    assert run([tmp_path]).ok


def test_wrong_kind_is_ignored_by_discovery(tmp_path: Path):
    record = valid_state_boundary_contract()
    record["kind"] = "not-a-state-boundary-contract"
    _write_record(tmp_path, record, "stranger.yaml")

    assert run([tmp_path]).ok


def test_tmp_file_is_skipped(tmp_path: Path):
    (tmp_path / "x.yaml.tmp.123").write_text(
        yaml.safe_dump({"kind": "state-boundary-contract"}), encoding="utf-8"
    )

    assert run([tmp_path]).ok


def test_schemas_directory_excluded(tmp_path: Path):
    record = valid_state_boundary_contract()
    record_path = tmp_path / "schemas" / "state-boundary-contract.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    assert run([tmp_path]).ok
