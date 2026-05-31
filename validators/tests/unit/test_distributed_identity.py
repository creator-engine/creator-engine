"""TDD coverage for the G2.004.2 distributed-identity substrate.

Two shape-only record families: federated identity bindings (cross-repo identity
binding) and distributed claims (cross-repo / team-mode coordination claim
primitive). Both are decoupled from CE-event and PCL runtime code.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.distributed_identity import (
    DC_CHECK_NAME,
    DC_CODE_CHAIN_LINK,
    DC_CODE_CONTENT_ADDRESS,
    DC_CODE_MODE_ENUM,
    DC_CODE_NO_INLINE,
    DC_CODE_POINTER_SHAPE,
    DC_CODE_RECORD_KIND,
    DC_CODE_ROLE_FLOOR,
    DC_CODE_SCHEMA,
    DC_CODE_SIGNATURE_SHAPE,
    DC_CODE_WRITE_FREEZE,
    FIB_CHECK_NAME,
    FIB_CODE_BINDING_SHAPE,
    FIB_CODE_CHAIN_LINK,
    FIB_CODE_CONTENT_ADDRESS,
    FIB_CODE_MODE_ENUM,
    FIB_CODE_NO_INLINE,
    FIB_CODE_RECORD_KIND,
    FIB_CODE_ROLE_FLOOR,
    FIB_CODE_SCHEMA,
    FIB_CODE_SIGNATURE_SHAPE,
    FIB_CODE_WRITE_FREEZE,
    run_distributed_claim,
    run_federated_identity_binding,
    validate_dc_file,
    validate_fib_file,
)


def _codes(errors) -> set[str]:
    return {error.code for error in errors}


def _fib_fixture(name: str) -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "federated-identity-binding" / name


def _dc_fixture(name: str) -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "distributed-claim" / name


# --- registration -------------------------------------------------------------
def test_checks_registered():
    checks = registered_checks()
    assert FIB_CHECK_NAME in checks
    assert DC_CHECK_NAME in checks
    fib_frs = checks[FIB_CHECK_NAME].frs
    for code in (
        FIB_CODE_SCHEMA,
        FIB_CODE_CONTENT_ADDRESS,
        FIB_CODE_CHAIN_LINK,
        FIB_CODE_RECORD_KIND,
        FIB_CODE_ROLE_FLOOR,
        FIB_CODE_MODE_ENUM,
        FIB_CODE_BINDING_SHAPE,
        FIB_CODE_SIGNATURE_SHAPE,
        FIB_CODE_NO_INLINE,
        FIB_CODE_WRITE_FREEZE,
    ):
        assert code in fib_frs
    dc_frs = checks[DC_CHECK_NAME].frs
    for code in (
        DC_CODE_SCHEMA,
        DC_CODE_CONTENT_ADDRESS,
        DC_CODE_CHAIN_LINK,
        DC_CODE_RECORD_KIND,
        DC_CODE_ROLE_FLOOR,
        DC_CODE_MODE_ENUM,
        DC_CODE_POINTER_SHAPE,
        DC_CODE_SIGNATURE_SHAPE,
        DC_CODE_NO_INLINE,
        DC_CODE_WRITE_FREEZE,
    ):
        assert code in dc_frs


# --- federated identity binding family ---------------------------------------
def test_fib_valid_binding_fixture_passes():
    errors = validate_fib_file(_fib_fixture("valid-binding.ce.yml"))
    assert errors == [], [e.format() for e in errors]


def test_fib_rejects_agent_ratifier_as_emitting_role():
    assert FIB_CODE_ROLE_FLOOR in _codes(validate_fib_file(_fib_fixture("invalid-agent-ratifier-role.ce.yml")))


def test_fib_rejects_malformed_signature_shape():
    assert FIB_CODE_SIGNATURE_SHAPE in _codes(validate_fib_file(_fib_fixture("invalid-signature-shape.ce.yml")))


def test_fib_rejects_inline_metadata_in_markdown():
    assert FIB_CODE_NO_INLINE in _codes(validate_fib_file(_fib_fixture("invalid-inline-metadata.md")))


def test_fib_rejects_binding_without_cross_repo_shape(tmp_path: Path):
    scope = tmp_path / "federated-identity-binding"
    scope.mkdir()
    path = scope / "single-repo-binding.ce.yml"
    record = {
        "record_id": "fib-tmp-0000",
        "record_kind": "federated_identity_binding",
        "sequence": 0,
        "parent_hash": None,
        "emitting_role": "operator",
        "operating_mode": "strict",
        "recorded_at": "2026-05-31T11:00:00Z",
        "body": {"principal_id": "prn-x", "repo_bindings": [{"repo_id": "repo-a", "identity_ref": "id-a"}]},
        "signature": {"scheme": "reserved-shape-only", "key_id": "operator-reserved", "value": "reserved-inactive"},
    }
    from creator_engine_validator.checks.distributed_identity import _canonical_hash

    record["content_hash"] = _canonical_hash(record)
    path.write_text(yaml.safe_dump({"federated_identity_binding": record}), encoding="utf-8")
    assert FIB_CODE_BINDING_SHAPE in _codes(validate_fib_file(path))


def test_fib_rejects_schema_violation(tmp_path: Path):
    scope = tmp_path / "federated-identity-binding"
    scope.mkdir()
    path = scope / "missing-fields.ce.yml"
    path.write_text(yaml.safe_dump({"federated_identity_binding": {"record_id": "fib-bad"}}), encoding="utf-8")
    assert FIB_CODE_SCHEMA in _codes(validate_fib_file(path))


def test_fib_run_over_fixture_dir_reports_malformed_codes():
    result = run_federated_identity_binding([_fib_fixture("valid-binding.ce.yml").parent])
    assert not result.ok
    codes = _codes(result.errors)
    assert FIB_CODE_ROLE_FLOOR in codes
    assert FIB_CODE_SIGNATURE_SHAPE in codes
    assert FIB_CODE_NO_INLINE in codes


# --- distributed claim family ------------------------------------------------
def test_dc_valid_linked_chain_fixture_passes():
    errors = validate_dc_file(_dc_fixture("valid-linked-chain.ce.yml"))
    assert errors == [], [e.format() for e in errors]


def test_dc_rejects_forged_content_hash_fixture():
    assert DC_CODE_CONTENT_ADDRESS in _codes(validate_dc_file(_dc_fixture("invalid-forged-hash.ce.yml")))


def test_dc_rejects_broken_parent_hash_fixture():
    codes = _codes(validate_dc_file(_dc_fixture("invalid-broken-chain.ce.yml")))
    assert DC_CODE_CHAIN_LINK in codes
    # The broken record's own digest is self-consistent, so only chain linkage fails.
    assert DC_CODE_CONTENT_ADDRESS not in codes


def test_dc_rejects_unknown_record_kind_fixture():
    assert DC_CODE_RECORD_KIND in _codes(validate_dc_file(_dc_fixture("invalid-unknown-record-kind.ce.yml")))


def test_dc_rejects_bad_pointer_fixture():
    codes = _codes(validate_dc_file(_dc_fixture("invalid-bad-pointer.ce.yml")))
    assert DC_CODE_POINTER_SHAPE in codes
    # Pointer shape is a semantic check, not a schema constraint.
    assert DC_CODE_SCHEMA not in codes


def test_dc_rejects_unknown_operating_mode_fixture():
    assert DC_CODE_MODE_ENUM in _codes(validate_dc_file(_dc_fixture("invalid-unknown-mode.ce.yml")))


def test_dc_rejects_legacy_hermes_write_target_fixture():
    codes = _codes(validate_dc_file(_dc_fixture("invalid-hermes-write.ce.yml")))
    assert DC_CODE_WRITE_FREEZE in codes
    # Write-freeze must be the only semantic failure (record is otherwise well-formed).
    assert DC_CODE_CONTENT_ADDRESS not in codes


def test_dc_rejects_inline_metadata_in_markdown(tmp_path: Path):
    scope = tmp_path / "distributed-claim"
    scope.mkdir()
    path = scope / "inline.md"
    path.write_text("# doc\n\n```yaml\ndistributed_claim:\n  record_id: dc-inline\n```\n", encoding="utf-8")
    assert DC_CODE_NO_INLINE in _codes(validate_dc_file(path))


def test_dc_rejects_schema_violation(tmp_path: Path):
    scope = tmp_path / "distributed-claim"
    scope.mkdir()
    path = scope / "missing-fields.ce.yml"
    path.write_text(yaml.safe_dump({"distributed_claim": {"record_id": "dc-bad"}}), encoding="utf-8")
    assert DC_CODE_SCHEMA in _codes(validate_dc_file(path))


def test_dc_run_over_fixture_dir_reports_malformed_codes():
    result = run_distributed_claim([_dc_fixture("valid-linked-chain.ce.yml").parent])
    assert not result.ok
    codes = _codes(result.errors)
    assert DC_CODE_CONTENT_ADDRESS in codes
    assert DC_CODE_CHAIN_LINK in codes
    assert DC_CODE_RECORD_KIND in codes
    assert DC_CODE_POINTER_SHAPE in codes
    assert DC_CODE_MODE_ENUM in codes
    assert DC_CODE_WRITE_FREEZE in codes


# --- scope + decoupling -------------------------------------------------------
def test_out_of_scope_yaml_is_ignored(tmp_path: Path):
    fib = tmp_path / "docs" / "random-fib.ce.yml"
    fib.parent.mkdir(parents=True)
    fib.write_text(yaml.safe_dump({"federated_identity_binding": {"operating_mode": "permissive"}}), encoding="utf-8")
    dc = tmp_path / "docs" / "random-dc.ce.yml"
    dc.write_text(yaml.safe_dump({"distributed_claim": {"operating_mode": "permissive"}}), encoding="utf-8")
    assert run_federated_identity_binding([tmp_path]).ok
    assert run_distributed_claim([tmp_path]).ok


def test_substrate_does_not_import_ce_event_or_pcl_code():
    """Spec S3: the substrate must not couple to CE-event or PCL runtime code."""
    import creator_engine_validator.checks.distributed_identity as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "ce_event_block" not in source
    assert "pcl_record" not in source
