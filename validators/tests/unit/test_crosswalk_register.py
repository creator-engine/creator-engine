"""Unit tests for the G2.001.4 crosswalk-register validator."""

from __future__ import annotations

from pathlib import Path

from creator_engine_validator import cli
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.crosswalk_register import (
    CHECK_NAME,
    CODE_AUTHORITATIVE,
    CODE_CANONICAL_MAPPING,
    CODE_CONTEXT_DISPOSITION,
    CODE_DERIVED_SUPERSEDES,
    CODE_SCHEMA_IDENTITY,
    run,
    validate_file,
)


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = checks[CHECK_NAME].frs
    assert CODE_AUTHORITATIVE in frs
    assert CODE_CANONICAL_MAPPING in frs
    assert CODE_CONTEXT_DISPOSITION in frs


def test_real_canonical_crosswalk_register_passes(repo_root: Path):
    path = repo_root / "specs/v2/_crosswalk.yml"
    errors = validate_file(path)
    assert errors == [], [error.format() for error in errors]


def test_well_formed_fixture_passes(examples_root: Path):
    path = examples_root / "well-formed/crosswalk-register/canonical-crosswalk.yml"
    errors = validate_file(path)
    assert errors == [], [error.format() for error in errors]


def test_missing_authoritative_true_fails(examples_root: Path):
    path = examples_root / "malformed/crosswalk-register/missing-authoritative.yml"
    assert CODE_AUTHORITATIVE in _codes(validate_file(path))


def test_missing_canonical_mapping_group_fails(examples_root: Path):
    path = examples_root / "malformed/crosswalk-register/missing-canonical-mappings.yml"
    assert CODE_CANONICAL_MAPPING in _codes(validate_file(path))


def test_derived_material_superseding_tracked_register_fails(examples_root: Path):
    path = examples_root / "malformed/crosswalk-register/derived-supersedes-authoritative.yml"
    assert CODE_DERIVED_SUPERSEDES in _codes(validate_file(path))


def test_malformed_context_disposition_fails(tmp_path: Path):
    path = tmp_path / "specs" / "v2" / "_crosswalk.yml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "schema: creator-engine/crosswalk-register\n"
        "schema_version: '2.0.0-draft'\n"
        "authoritative: true\n"
        "derived_material_note: tracked register is authoritative and not superseded by derived material\n"
        "roles:\n  - source: source\n    operator: operator\n    disposition: import-alias-only\n"
        "state_paths:\n  active_state_root:\n    v1: .hermes/\n    v2: .ce/\n"
        "feature_labels:\n  - v1_label: Feature 008\n    v2: specs/v2/005\n"
        "sidecars:\n  - v1: spec.creator-engine.yml\n    v2: spec.ce.yml\n"
        "other_axes:\n  - axis: gate-numbering\n    v1: G0..G8 / PCO Slice 0..6\n    v2: G2.<feature>.<slice>\n"
        "context_disposition:\n"
        "  v1_archived_import_context:\n    rules: [Readable, and may be emitted by new v2 artifacts.]\n"
        "  v2_canonical_emission_context:\n    rules: [Canonical for all new Phase 2 artifacts.]\n",
        encoding="utf-8",
    )
    assert CODE_CONTEXT_DISPOSITION in _codes(validate_file(path))


def test_wrong_schema_identity_fails(tmp_path: Path):
    path = tmp_path / "specs" / "v2" / "_crosswalk.yml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "schema: creator-engine/not-crosswalk\n"
        "schema_version: '2.0.0-draft'\n"
        "authoritative: true\n",
        encoding="utf-8",
    )
    assert CODE_SCHEMA_IDENTITY in _codes(validate_file(path))


def test_run_over_well_formed_dir_passes(examples_root: Path):
    result = run([examples_root / "well-formed/crosswalk-register"])
    assert result.ok, [error.format() for error in result.errors]


def test_run_over_malformed_dir_fails_closed(examples_root: Path):
    result = run([examples_root / "malformed/crosswalk-register"])
    assert not result.ok
    assert {
        CODE_AUTHORITATIVE,
        CODE_CANONICAL_MAPPING,
        CODE_DERIVED_SUPERSEDES,
    }.issubset(_codes(result.errors))


def test_cli_subcommand_dispatches_crosswalk_register(examples_root: Path, capsys):
    exit_code = cli.main(["scan-crosswalk-register", str(examples_root / "well-formed/crosswalk-register")])
    assert exit_code == 0
    assert "PASS crosswalk_register" in capsys.readouterr().out
