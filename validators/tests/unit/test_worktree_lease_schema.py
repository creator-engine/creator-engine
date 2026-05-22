"""Unit tests for the PCO Slice 2A / PCO-024 ``worktree_lease_schema`` check.

The check validates one Worktree Lease record at a time against
``schemas/worktree-lease.schema.yaml`` and emits ``PCO-020`` failures
that cite ``docs/operations/WORKTREE_LEASE_PROTOCOL.md``.

PCO-024 signature validation is exercised via ``validate_lease_signature``
and ``run``.

The check is record-level: it MUST NOT cross-check lease/lease or
lease/claim relationships (those are owned by
``active_work_ledger_conflicts``). It MUST tolerate orphaned
``*.tmp.*`` atomic-write artifacts the same way the Slice 0 schema
check does.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.worktree_lease_schema import (
    CHECK_NAME,
    CODE_SCHEMA,
    CODE_SIGNATURE,
    run,
    validate_lease_signature,
    validate_worktree_lease_record,
)


def valid_lease_record() -> dict:
    return {
        "kind": "worktree-lease-record",
        "record_type": "worktree_lease",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice2a-author",
        "record_timestamp": "2026-05-21T03:08:08Z",
        "lease_id": "lease-pco-slice2a-001",
        "worktree_path": "/home/example/projects/creator-engine-worktrees/pco-slice2a",
        "acquired_at": "2026-05-21T03:08:08Z",
        "lease_seconds": 3600,
        "expires_at": "2026-05-21T04:08:08Z",
    }


def test_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SCHEMA in checks[CHECK_NAME].frs


def test_well_formed_lease_record_passes(tmp_path: Path):
    record = valid_lease_record()
    assert validate_worktree_lease_record(record, tmp_path / "lease.yaml") == []


def test_well_formed_lease_with_optional_fields_passes(tmp_path: Path):
    record = valid_lease_record()
    record["pane_label"] = "implementer"
    record["branch"] = "pco-slice-2a-feature"
    record["envelope_ref"] = ".hermes/envelopes/pco-slice2a.md"
    record["note"] = "Optional human-readable hint for the operator."
    assert validate_worktree_lease_record(record, tmp_path / "lease.yaml") == []


def test_missing_required_field_fails(tmp_path: Path):
    for field in (
        "lease_id",
        "worktree_path",
        "acquired_at",
        "lease_seconds",
        "expires_at",
        "controller_id",
        "lane_id",
        "record_timestamp",
    ):
        record = valid_lease_record()
        del record[field]
        errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
        assert errors, f"expected schema error for missing {field!r}"
        assert any(error.code == CODE_SCHEMA for error in errors)
        assert all(
            error.contract == "docs/operations/WORKTREE_LEASE_PROTOCOL.md"
            for error in errors
        )


def test_bad_controller_id_pattern_fails(tmp_path: Path):
    record = valid_lease_record()
    record["controller_id"] = "Bad_ID"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("controller_id" in error.path for error in errors)


def test_bad_lane_id_pattern_fails(tmp_path: Path):
    record = valid_lease_record()
    record["lane_id"] = "Bad_Lane_ID"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("lane_id" in error.path for error in errors)


def test_lease_seconds_below_minimum_fails(tmp_path: Path):
    record = valid_lease_record()
    record["lease_seconds"] = 30
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("lease_seconds" in error.path for error in errors)


def test_lease_seconds_above_maximum_fails(tmp_path: Path):
    record = valid_lease_record()
    record["lease_seconds"] = 90000
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("lease_seconds" in error.path for error in errors)


def test_bad_lease_id_pattern_fails(tmp_path: Path):
    record = valid_lease_record()
    record["lease_id"] = "Bad Lease ID!"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("lease_id" in error.path for error in errors)


def test_invalid_expires_at_shape_fails(tmp_path: Path):
    record = valid_lease_record()
    record["expires_at"] = "soon"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("expires_at" in error.path for error in errors)


def test_invalid_acquired_at_shape_fails(tmp_path: Path):
    record = valid_lease_record()
    record["acquired_at"] = "yesterday"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("acquired_at" in error.path for error in errors)


def test_unknown_top_level_field_fails(tmp_path: Path):
    record = valid_lease_record()
    record["unexpected_stray_field"] = "not allowed"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any(error.code == CODE_SCHEMA for error in errors)


def test_pane_label_enum_constrained(tmp_path: Path):
    record = valid_lease_record()
    record["pane_label"] = "some-tool-binding"
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any("pane_label" in error.path for error in errors)


def test_wrong_kind_field_is_ignored_by_discovery(tmp_path: Path):
    record = valid_lease_record()
    record["kind"] = "not-a-lease-record"
    record_path = tmp_path / "stranger.yaml"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_tmp_file_is_skipped(tmp_path: Path):
    # Orphaned atomic-write temp file must be skipped without erroring.
    bad_record = {"kind": "worktree-lease-record", "record_type": "worktree_lease"}
    tmp_file = tmp_path / "lease.yaml.tmp.12345.abcdef"
    tmp_file.write_text(yaml.safe_dump(bad_record), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_well_formed_lease_under_directory_passes(tmp_path: Path):
    record = valid_lease_record()
    record_path = tmp_path / "leases" / "hermes-primary" / "lease.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok, f"unexpected errors: {[e.format() for e in result.errors]}"


def test_schemas_directory_excluded_from_discovery(tmp_path: Path):
    # The validator MUST NOT pick up files under a ``schemas/`` path so
    # that the canonical schema itself does not self-validate.
    record = valid_lease_record()
    record_path = tmp_path / "schemas" / "lease.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok


# ---------------------------------------------------------------------------
# PCO-024 schema version 2 / signature tests
# ---------------------------------------------------------------------------

VALID_PUBLIC_KEY = "lIXLPF6UGwuxA5uKroFNxMuvdOFzShfHcPO1Dt_YN1Q"
VALID_SIGNATURE = "JsL8fPIm6dM_ahcTB5sWFPuM0Fuf9xwAtVj6sZqpk_WoZnew7yf6pATGEin7YIHCj4k8cbaLtGtgdmWd4B42Aw"


def valid_controller_key_record() -> dict:
    return {
        "kind": "controller-key-record",
        "record_type": "controller_key",
        "schema_version": "1",
        "tenant_id": "dogfood",
        "controller_id": "hermes-primary",
        "key_algorithm": "ed25519",
        "public_key": {
            "encoding": "base64url-no-padding",
            "value": VALID_PUBLIC_KEY,
        },
        "issued_at": "2026-05-22T15:00:00Z",
        "issued_by": "source-controlled:tenants/dogfood/identity.yaml",
        "key_custody_mode": "per_host",
        "status": "active",
    }


def valid_signed_lease_record() -> dict:
    return {
        "kind": "worktree-lease-record",
        "record_type": "worktree_lease",
        "schema_version": "2",
        "controller_id": "hermes-primary",
        "lane_id": "pco-024-signed-example",
        "record_timestamp": "2026-05-22T16:00:00Z",
        "lease_id": "lease-signed-example-001",
        "worktree_path": "/worktrees/pco-024-signed",
        "acquired_at": "2026-05-22T16:00:00Z",
        "lease_seconds": 3600,
        "expires_at": "9999-01-01T00:00:00Z",
        "worktree_lease_signature": {
            "algorithm": "ed25519",
            "canonicalization": "creator-engine/worktree-lease-signature/v1",
            "key_ref": "tenants/dogfood/controllers/hermes-primary.key.yaml",
            "value": VALID_SIGNATURE,
        },
    }


def _make_key_lookup(
    key_ref: str,
    key_record: dict,
    key_path: Path,
) -> dict:
    return {key_ref: (key_path, key_record)}


def test_pco024_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_SIGNATURE in checks[CHECK_NAME].frs


def test_v2_schema_valid_passes(tmp_path: Path):
    record = valid_signed_lease_record()
    assert validate_worktree_lease_record(record, tmp_path / "lease.yaml") == []


def test_v1_with_signature_field_fails_schema(tmp_path: Path):
    record = valid_lease_record()
    record["worktree_lease_signature"] = {
        "algorithm": "ed25519",
        "canonicalization": "creator-engine/worktree-lease-signature/v1",
        "key_ref": "tenants/dogfood/controllers/hermes-primary.key.yaml",
        "value": VALID_SIGNATURE,
    }
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)


def test_v2_without_signature_field_fails_schema(tmp_path: Path):
    record = valid_signed_lease_record()
    del record["worktree_lease_signature"]
    errors = validate_worktree_lease_record(record, tmp_path / "lease.yaml")
    assert errors
    assert any(e.code == CODE_SCHEMA for e in errors)


def test_v2_valid_signature_passes(tmp_path: Path):
    record = valid_signed_lease_record()
    key_path = tmp_path / "tenants/dogfood/controllers/hermes-primary.key.yaml"
    lookup = _make_key_lookup(
        "tenants/dogfood/controllers/hermes-primary.key.yaml",
        valid_controller_key_record(),
        key_path,
    )
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", lookup)
    assert errors == [], [e.format() for e in errors]


def test_v1_record_skipped_by_signature_check(tmp_path: Path):
    record = valid_lease_record()
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", {})
    assert errors == []


def test_pco024_unknown_controller_key(tmp_path: Path):
    record = valid_signed_lease_record()
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", {})
    assert errors
    assert any(e.code == CODE_SIGNATURE and "not found" in e.message for e in errors)


def test_pco024_revoked_controller_key(tmp_path: Path):
    record = valid_signed_lease_record()
    key_record = valid_controller_key_record()
    key_record["status"] = "revoked"
    key_record["revoked_at"] = "2026-05-22T17:00:00Z"
    key_path = tmp_path / "tenants/dogfood/controllers/hermes-primary.key.yaml"
    lookup = _make_key_lookup(
        "tenants/dogfood/controllers/hermes-primary.key.yaml",
        key_record,
        key_path,
    )
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", lookup)
    assert errors
    assert any(e.code == CODE_SIGNATURE and "revoked" in e.message for e in errors)


def test_pco024_controller_id_mismatch(tmp_path: Path):
    record = valid_signed_lease_record()
    key_record = valid_controller_key_record()
    key_record["controller_id"] = "other-controller"
    key_path = tmp_path / "tenants/dogfood/controllers/hermes-primary.key.yaml"
    lookup = _make_key_lookup(
        "tenants/dogfood/controllers/hermes-primary.key.yaml",
        key_record,
        key_path,
    )
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", lookup)
    assert errors
    assert any(e.code == CODE_SIGNATURE and "controller_id" in e.message for e in errors)


def test_pco024_malformed_signature_bytes(tmp_path: Path):
    record = valid_signed_lease_record()
    record["worktree_lease_signature"]["value"] = "not+base64url/bad=="
    key_path = tmp_path / "tenants/dogfood/controllers/hermes-primary.key.yaml"
    lookup = _make_key_lookup(
        "tenants/dogfood/controllers/hermes-primary.key.yaml",
        valid_controller_key_record(),
        key_path,
    )
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", lookup)
    assert errors
    assert any(e.code == CODE_SIGNATURE and "base64url" in e.message for e in errors)


def test_pco024_wrong_signature_length(tmp_path: Path):
    record = valid_signed_lease_record()
    record["worktree_lease_signature"]["value"] = "AAAA"
    key_path = tmp_path / "tenants/dogfood/controllers/hermes-primary.key.yaml"
    lookup = _make_key_lookup(
        "tenants/dogfood/controllers/hermes-primary.key.yaml",
        valid_controller_key_record(),
        key_path,
    )
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", lookup)
    assert errors
    assert any(e.code == CODE_SIGNATURE and "64 bytes" in e.message for e in errors)


def test_pco024_signature_verification_failure(tmp_path: Path):
    record = valid_signed_lease_record()
    record["worktree_lease_signature"]["value"] = (
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    )
    key_path = tmp_path / "tenants/dogfood/controllers/hermes-primary.key.yaml"
    lookup = _make_key_lookup(
        "tenants/dogfood/controllers/hermes-primary.key.yaml",
        valid_controller_key_record(),
        key_path,
    )
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", lookup)
    assert errors
    assert any(e.code == CODE_SIGNATURE and "verification failed" in e.message for e in errors)


def test_v2_signed_lease_passes_via_run(tmp_path: Path):
    key_dir = tmp_path / "tenants" / "dogfood" / "controllers"
    key_dir.mkdir(parents=True)
    key_path = key_dir / "hermes-primary.key.yaml"
    key_path.write_text(yaml.safe_dump(valid_controller_key_record()), encoding="utf-8")

    lease_path = tmp_path / "lease.yaml"
    lease_path.write_text(yaml.safe_dump(valid_signed_lease_record()), encoding="utf-8")

    result = run([tmp_path])
    assert result.ok, [e.format() for e in result.errors]


def test_pco024_invalid_key_algorithm_fails(tmp_path: Path):
    record = valid_signed_lease_record()
    key_record = valid_controller_key_record()
    key_record["key_algorithm"] = "rsa"
    key_path = tmp_path / "tenants/dogfood/controllers/hermes-primary.key.yaml"
    lookup = _make_key_lookup(
        "tenants/dogfood/controllers/hermes-primary.key.yaml",
        key_record,
        key_path,
    )
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", lookup)
    assert errors
    assert any(e.code == CODE_SIGNATURE and "PCO-025" in e.message for e in errors)


def test_pco024_invalid_key_encoding_fails(tmp_path: Path):
    record = valid_signed_lease_record()
    key_record = valid_controller_key_record()
    key_record["public_key"]["encoding"] = "hex"
    key_path = tmp_path / "tenants/dogfood/controllers/hermes-primary.key.yaml"
    lookup = _make_key_lookup(
        "tenants/dogfood/controllers/hermes-primary.key.yaml",
        key_record,
        key_path,
    )
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", lookup)
    assert errors
    assert any(e.code == CODE_SIGNATURE and "PCO-025" in e.message for e in errors)


def test_pco024_canonicalization_error_no_crash(tmp_path: Path):
    import datetime

    record = valid_signed_lease_record()
    record["acquired_at"] = datetime.date(2026, 5, 22)
    key_path = tmp_path / "tenants/dogfood/controllers/hermes-primary.key.yaml"
    lookup = _make_key_lookup(
        "tenants/dogfood/controllers/hermes-primary.key.yaml",
        valid_controller_key_record(),
        key_path,
    )
    errors = validate_lease_signature(record, tmp_path / "lease.yaml", lookup)
    assert errors
    assert any(e.code == CODE_SIGNATURE for e in errors)


def test_schema_invalid_v2_lease_skips_pco024(tmp_path: Path):
    # A YAML bare date parses as datetime.date (non-JSON-serializable, schema-invalid).
    # The validator must not crash and must report PCO-020, not a PCO-024 error cascade.
    raw_yaml = (
        'kind: worktree-lease-record\n'
        'record_type: worktree_lease\n'
        'schema_version: "2"\n'
        'controller_id: hermes-primary\n'
        'lane_id: pco-024-signed-example\n'
        'record_timestamp: "2026-05-22T16:00:00Z"\n'
        'lease_id: lease-signed-example-001\n'
        'worktree_path: /worktrees/pco-024-signed\n'
        'acquired_at: 2026-05-22\n'
        'lease_seconds: 3600\n'
        'expires_at: "9999-01-01T00:00:00Z"\n'
        'worktree_lease_signature:\n'
        '  algorithm: ed25519\n'
        '  canonicalization: creator-engine/worktree-lease-signature/v1\n'
        '  key_ref: tenants/dogfood/controllers/hermes-primary.key.yaml\n'
        f'  value: {VALID_SIGNATURE}\n'
    )
    lease_path = tmp_path / "lease.yaml"
    lease_path.write_text(raw_yaml, encoding="utf-8")

    result = run([tmp_path])
    assert not result.ok
    assert any(e.code == CODE_SCHEMA for e in result.errors)
    assert not any(e.code == CODE_SIGNATURE for e in result.errors)


def test_pco024_ambiguous_key_ref_fails_closed(tmp_path: Path):
    # Two packages each with a key and a signed lease using the same key_ref.
    # When scanned together both lease parents contribute "tenants/..." as a root,
    # mapping the same relative key_ref to two distinct physical files → ambiguous.
    for pkg in ("lease-a", "lease-b"):
        pkg_dir = tmp_path / pkg
        key_dir = pkg_dir / "tenants" / "dogfood" / "controllers"
        key_dir.mkdir(parents=True)
        (key_dir / "hermes-primary.key.yaml").write_text(
            yaml.safe_dump(valid_controller_key_record()), encoding="utf-8"
        )
        (pkg_dir / "lease.yaml").write_text(
            yaml.safe_dump(valid_signed_lease_record()), encoding="utf-8"
        )

    result = run([tmp_path])
    assert not result.ok
    assert any(e.code == CODE_SIGNATURE for e in result.errors)


def test_pco024_unrelated_nested_tenants_key_not_trusted(tmp_path: Path):
    # A key under a nested tenants/ subtree that is NOT a lease parent directory
    # must not satisfy a key_ref — only exact relative paths from scan roots and
    # lease parent dirs are accepted.
    unrelated = tmp_path / "unrelated-subtree"
    key_dir = unrelated / "tenants" / "dogfood" / "controllers"
    key_dir.mkdir(parents=True)
    (key_dir / "hermes-primary.key.yaml").write_text(
        yaml.safe_dump(valid_controller_key_record()), encoding="utf-8"
    )

    lease_path = tmp_path / "lease.yaml"
    lease_path.write_text(yaml.safe_dump(valid_signed_lease_record()), encoding="utf-8")

    result = run([tmp_path])
    assert not result.ok
    assert any(e.code == CODE_SIGNATURE and "not found" in e.message for e in result.errors)


def test_v2_bad_sig_fails_via_run(tmp_path: Path):
    key_dir = tmp_path / "tenants" / "dogfood" / "controllers"
    key_dir.mkdir(parents=True)
    key_path = key_dir / "hermes-primary.key.yaml"
    key_path.write_text(yaml.safe_dump(valid_controller_key_record()), encoding="utf-8")

    record = valid_signed_lease_record()
    record["worktree_lease_signature"]["value"] = (
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    )
    lease_path = tmp_path / "lease.yaml"
    lease_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    result = run([tmp_path])
    assert not result.ok
    assert any(e.code == CODE_SIGNATURE for e in result.errors)
