"""TDD coverage for G2.004.0 PCL (Project Coordination Ledger) record substrate."""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.pcl_record import (
    CHECK_NAME,
    CODE_CHAIN_LINK,
    CODE_CONTENT_ADDRESS,
    CODE_MODE_ENUM,
    CODE_NO_INLINE,
    CODE_POINTER_SHAPE,
    CODE_RECORD_KIND,
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
    return Path(__file__).resolve().parents[2] / "examples" / "pcl-record" / name


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    frs = checks[CHECK_NAME].frs
    assert CODE_SCHEMA in frs
    assert CODE_CONTENT_ADDRESS in frs
    assert CODE_CHAIN_LINK in frs
    assert CODE_RECORD_KIND in frs
    assert CODE_ROLE_FLOOR in frs
    assert CODE_MODE_ENUM in frs
    assert CODE_POINTER_SHAPE in frs
    assert CODE_SIGNATURE_SHAPE in frs
    assert CODE_NO_INLINE in frs
    assert CODE_WRITE_FREEZE in frs


def test_valid_linked_chain_fixture_passes():
    errors = validate_file(_fixture("valid-linked-chain.ce.yml"))
    assert errors == [], [e.format() for e in errors]


def test_rejects_forged_content_hash_fixture():
    assert CODE_CONTENT_ADDRESS in _codes(validate_file(_fixture("invalid-forged-hash.ce.yml")))


def test_rejects_broken_parent_hash_fixture():
    codes = _codes(validate_file(_fixture("invalid-broken-chain.ce.yml")))
    assert CODE_CHAIN_LINK in codes
    # The broken record's own digest is self-consistent, so only chain linkage fails.
    assert CODE_CONTENT_ADDRESS not in codes


def test_rejects_unknown_record_kind_fixture():
    assert CODE_RECORD_KIND in _codes(validate_file(_fixture("invalid-unknown-record-kind.ce.yml")))


def test_rejects_agent_ratifier_as_emitting_role():
    assert CODE_ROLE_FLOOR in _codes(validate_file(_fixture("invalid-agent-ratifier-role.ce.yml")))


def test_rejects_unknown_operating_mode():
    assert CODE_MODE_ENUM in _codes(validate_file(_fixture("invalid-unknown-mode.ce.yml")))


def test_rejects_malformed_signature_shape():
    assert CODE_SIGNATURE_SHAPE in _codes(validate_file(_fixture("invalid-signature-shape.ce.yml")))


def test_rejects_inline_pcl_metadata_in_markdown():
    assert CODE_NO_INLINE in _codes(validate_file(_fixture("invalid-inline-metadata.md")))


def test_rejects_legacy_hermes_pcl_write_target():
    assert CODE_WRITE_FREEZE in _codes(validate_file(_fixture("invalid-hermes-write.ce.yml")))


def test_rejects_malformed_event_block_pointer(tmp_path: Path):
    # event_block_pointer must carry an opaque 64-hex ce_event_content_hash.
    scope = tmp_path / "pcl-record"
    scope.mkdir()
    path = scope / "bad-pointer.ce.yml"
    path.write_text(
        yaml.safe_dump(
            {
                "pcl_record": {
                    "record_id": "pcl-g20040-9999",
                    "record_kind": "event_block_pointer",
                    "sequence": 0,
                    "parent_hash": None,
                    "content_hash": "0" * 64,
                    "emitting_role": "controller",
                    "operating_mode": "strict",
                    "recorded_at": "2026-05-31T07:00:00Z",
                    "body": {"ce_event_content_hash": "not-a-valid-hash", "stream": "x"},
                    "signature": {
                        "scheme": "reserved-shape-only",
                        "key_id": "operator-reserved",
                        "value": "reserved-inactive",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    assert CODE_POINTER_SHAPE in _codes(validate_file(path))


def test_rejects_schema_violation(tmp_path: Path):
    scope = tmp_path / "pcl-record"
    scope.mkdir()
    path = scope / "missing-fields.ce.yml"
    # Missing most required fields -> schema rejects with VAL-PCL-SCHEMA.
    path.write_text(yaml.safe_dump({"pcl_record": {"record_id": "pcl-bad"}}), encoding="utf-8")
    assert CODE_SCHEMA in _codes(validate_file(path))


def test_run_over_fixture_dir_reports_malformed_fixture_codes():
    result = run([_fixture("valid-linked-chain.ce.yml").parent])
    assert not result.ok
    codes = _codes(result.errors)
    assert CODE_CONTENT_ADDRESS in codes
    assert CODE_CHAIN_LINK in codes
    assert CODE_RECORD_KIND in codes
    assert CODE_ROLE_FLOOR in codes
    assert CODE_MODE_ENUM in codes
    assert CODE_SIGNATURE_SHAPE in codes
    assert CODE_NO_INLINE in codes
    assert CODE_WRITE_FREEZE in codes


def test_out_of_scope_yaml_is_ignored(tmp_path: Path):
    path = tmp_path / "docs" / "random.ce.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({"pcl_record": {"operating_mode": "permissive"}}), encoding="utf-8")
    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]
