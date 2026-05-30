"""TDD coverage for G2.003.0 CE-event signed-block substrate."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.ce_event_block import (
    CHECK_NAME,
    CODE_CHAIN_LINK,
    CODE_CONTENT_ADDRESS,
    CODE_MODE_ENUM,
    CODE_NO_INLINE,
    CODE_ROLE_FLOOR,
    CODE_SCHEMA,
    CODE_SIGNATURE_SHAPE,
    CODE_WRITE_FREEZE,
    run,
    validate_file,
)


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def _fixture(name: str) -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "ce-event-block" / name


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = checks[CHECK_NAME].frs
    assert CODE_CONTENT_ADDRESS in frs
    assert CODE_CHAIN_LINK in frs
    assert CODE_ROLE_FLOOR in frs


def test_valid_linked_chain_fixture_passes():
    errors = validate_file(_fixture("valid-linked-chain.ce.yml"))
    assert errors == [], [e.format() for e in errors]


def test_rejects_forged_content_hash_fixture():
    assert CODE_CONTENT_ADDRESS in _codes(validate_file(_fixture("invalid-forged-hash.ce.yml")))


def test_rejects_broken_parent_hash_fixture():
    assert CODE_CHAIN_LINK in _codes(validate_file(_fixture("invalid-broken-chain.ce.yml")))


def test_rejects_agent_ratifier_as_emitting_role():
    assert CODE_ROLE_FLOOR in _codes(validate_file(_fixture("invalid-agent-ratifier-role.ce.yml")))


def test_rejects_unknown_operating_mode():
    assert CODE_MODE_ENUM in _codes(validate_file(_fixture("invalid-unknown-mode.ce.yml")))


def test_rejects_malformed_signature_shape():
    assert CODE_SIGNATURE_SHAPE in _codes(validate_file(_fixture("invalid-signature-shape.ce.yml")))


def test_rejects_inline_ce_event_metadata_in_markdown():
    assert CODE_NO_INLINE in _codes(validate_file(_fixture("invalid-inline-metadata.md")))


def test_rejects_legacy_hermes_active_state_write_target():
    assert CODE_WRITE_FREEZE in _codes(validate_file(_fixture("invalid-hermes-write.ce.yml")))


def test_run_over_fixture_dir_reports_malformed_fixture_codes():
    result = run([_fixture("valid-linked-chain.ce.yml").parent])
    assert not result.ok
    codes = _codes(result.errors)
    assert CODE_CONTENT_ADDRESS in codes
    assert CODE_CHAIN_LINK in codes
    assert CODE_ROLE_FLOOR in codes
    assert CODE_MODE_ENUM in codes
    assert CODE_SIGNATURE_SHAPE in codes
    assert CODE_WRITE_FREEZE in codes


def test_out_of_scope_yaml_is_ignored(tmp_path: Path):
    path = tmp_path / "docs" / "random.ce.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({"ce_event_block": {"operating_mode": "permissive"}}), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]
