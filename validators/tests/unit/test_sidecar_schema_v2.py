"""Unit tests for the G2.001.3 v2 sidecar schema/risk checks."""

from __future__ import annotations

from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.sidecar_schema_v2 import (
    CHECK_NAME,
    CODE_INLINE_METADATA,
    CODE_RISK_COVERAGE,
    CODE_SCHEMA,
    run,
    validate_markdown_file,
    validate_spec_sidecar,
)


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = checks[CHECK_NAME].frs
    assert CODE_INLINE_METADATA in frs
    assert CODE_RISK_COVERAGE in frs


def test_formal_schema_file_exists(repo_root: Path):
    assert (repo_root / "schemas/spec-ce-sidecar.schema.yaml").is_file()


def test_real_g20013_sidecar_passes(repo_root: Path):
    path = repo_root / "specs/v2/001-v2-foundation-substrate/spec.ce.yml"
    errors = validate_spec_sidecar(path)
    assert errors == [], [e.format() for e in errors]


def test_well_formed_fixture_passes(examples_root: Path):
    path = examples_root / "well-formed/sidecar-schema-v2/spec.ce.yml"
    errors = validate_spec_sidecar(path)
    assert errors == [], [e.format() for e in errors]


def test_markdown_with_inline_ce_metadata_fails(examples_root: Path):
    path = examples_root / "malformed/sidecar-schema-v2/inline-ce-metadata/spec.md"
    errors = validate_markdown_file(path)
    assert CODE_INLINE_METADATA in _codes(errors)


def test_markdown_front_matter_with_ce_metadata_fails(examples_root: Path):
    path = examples_root / "malformed/sidecar-schema-v2/frontmatter-ce-metadata/spec.md"
    errors = validate_markdown_file(path)
    assert CODE_INLINE_METADATA in _codes(errors)


def test_markdown_front_matter_without_ce_metadata_passes(tmp_path: Path):
    path = tmp_path / "specs" / "v2" / "plain-frontmatter.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "---\n"
        "title: Plain Spec Kit metadata\n"
        "owner: operator\n"
        "---\n"
        "\n"
        "# Plain spec\n",
        encoding="utf-8",
    )
    assert validate_markdown_file(path) == []


def test_missing_risk_inventory_for_risk_bearing_spec_fails(examples_root: Path):
    path = examples_root / "malformed/sidecar-schema-v2/missing-risk-inventory/spec.ce.yml"
    errors = validate_spec_sidecar(path)
    assert CODE_RISK_COVERAGE in _codes(errors)


def test_risk_refs_must_map_to_required_validation_and_back(examples_root: Path):
    path = examples_root / "malformed/sidecar-schema-v2/unmapped-risk-validation/spec.ce.yml"
    errors = validate_spec_sidecar(path)
    assert CODE_RISK_COVERAGE in _codes(errors)
    rendered = "\n".join(error.format() for error in errors)
    assert "VAL-MISSING" in rendered
    assert "VAL-ORPHAN" in rendered


def test_run_over_well_formed_dir_passes(examples_root: Path):
    result = run([examples_root / "well-formed/sidecar-schema-v2"])
    assert result.ok, [e.format() for e in result.errors]


def test_run_over_malformed_dir_fails_closed(examples_root: Path):
    result = run([examples_root / "malformed/sidecar-schema-v2"])
    assert not result.ok
    assert {CODE_INLINE_METADATA, CODE_RISK_COVERAGE}.issubset(_codes(result.errors))


def test_legacy_creator_engine_sidecars_are_not_forced_through_v2_schema(examples_root: Path):
    result = run([examples_root / "malformed/spec.creator-engine.missing-acceptance.yml"])
    assert result.ok, [e.format() for e in result.errors]
