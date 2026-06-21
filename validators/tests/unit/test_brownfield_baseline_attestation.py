from __future__ import annotations

import json
from pathlib import Path

import yaml
import pytest
from jsonschema import Draft202012Validator

from creator_engine_validator import v3_installer
from creator_engine_validator.checks import brownfield_baseline_attestation as chk
from creator_engine_validator.checks import registered_checks
from creator_engine_validator.schema import load_schema


BASELINE_SHA = "a" * 40
SNAPSHOT_DIGEST = "b" * 64


def _canonical_digest(record: dict) -> str:
    material = {key: value for key, value in record.items() if key != "content_digest"}
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return v3_installer.content_digest(raw)


def _record(**overrides) -> dict:
    record = v3_installer.brownfield_baseline_attestation_record(
        baseline_commit_sha=BASELINE_SHA,
        snapshot_content_digest=SNAPSHOT_DIGEST,
        scrub_result={
            "status": "clean",
            "scanners": [
                {"name": "trufflehog", "version": "3.90.5", "result": "clean"},
                {"name": "gitleaks", "version": "8.28.0", "result": "clean"},
            ],
        },
        attestor_ref="operator:peer-operator",
        attested_at="2026-06-21T08:30:00Z",
    )
    record.update(overrides)
    return record


def _schema_errors(record: dict) -> list:
    validator = Draft202012Validator(load_schema("schemas/brownfield-baseline-attestation.schema.yaml"))
    return sorted(validator.iter_errors(record), key=lambda err: list(err.path))


def test_builder_emits_schema_valid_value_free_record_with_content_digest():
    record = _record()

    assert record["kind"] == "brownfield-baseline-attestation"
    assert record["record_type"] == "brownfield_baseline_attestation"
    assert record["schema_version"] == "1"
    assert record["baseline_commit_sha"] == BASELINE_SHA
    assert record["snapshot"]["content_digest"] == SNAPSHOT_DIGEST
    assert record["scrub"]["status"] == "clean"
    assert [scanner["name"] for scanner in record["scrub"]["scanners"]] == ["gitleaks", "trufflehog"]
    assert record["content_digest"] == _canonical_digest(record)
    assert _schema_errors(record) == []


def test_builder_is_deterministic_for_equivalent_scanner_order():
    first = _record()
    second = v3_installer.brownfield_baseline_attestation_record(
        baseline_commit_sha=BASELINE_SHA,
        snapshot_content_digest=SNAPSHOT_DIGEST,
        scrub_result={
            "status": "clean",
            "scanners": [
                {"name": "gitleaks", "version": "8.28.0", "result": "clean"},
                {"name": "trufflehog", "version": "3.90.5", "result": "clean"},
            ],
        },
        attestor_ref="operator:peer-operator",
        attested_at="2026-06-21T08:30:00Z",
    )

    assert first == second


def test_schema_rejects_raw_scrub_findings_or_unknown_fields():
    record = _record()
    record["scrub"]["findings"] = [{"path": ".env", "secret": "raw"}]

    assert _schema_errors(record)


@pytest.mark.parametrize(
    "attestor_ref",
    [
        "https://github.com/creator-engine/creator-engine",
        "creator-engine.dev",
        "/home/operator/baseline",
        "docs/baseline.yaml",
        "operator.peer-operator",
    ],
)
def test_schema_rejects_value_bearing_attestor_refs(attestor_ref: str):
    record = _record()
    record["attestor_ref"] = attestor_ref

    assert _schema_errors(record)


@pytest.mark.parametrize(
    "attestor_ref",
    [
        "https://github.com/creator-engine/creator-engine",
        "creator-engine.dev",
        "/home/operator/baseline",
        "docs/baseline.yaml",
    ],
)
def test_registered_check_rejects_value_bearing_attestor_refs(tmp_path: Path, attestor_ref: str):
    record = _record()
    record["attestor_ref"] = attestor_ref
    path = tmp_path / "baseline.yaml"
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")

    result = chk.run([tmp_path])

    assert any(error.code == chk.CODE_VALUE_FREE for error in result.errors)


@pytest.mark.parametrize(
    "attestor_ref",
    [
        "https://github.com/creator-engine/creator-engine",
        "creator-engine.dev",
        "/home/operator/baseline",
        "docs/baseline.yaml",
    ],
)
def test_builder_rejects_value_bearing_attestor_refs(attestor_ref: str):
    with pytest.raises(ValueError, match="attestor_ref"):
        v3_installer.brownfield_baseline_attestation_record(
            baseline_commit_sha=BASELINE_SHA,
            snapshot_content_digest=SNAPSHOT_DIGEST,
            scrub_result={
                "status": "clean",
                "scanners": [{"name": "gitleaks", "version": "8.28.0", "result": "clean"}],
            },
            attestor_ref=attestor_ref,
            attested_at="2026-06-21T08:30:00Z",
        )


def test_registered_check_enforces_content_digest(tmp_path: Path):
    assert chk.CHECK_NAME in registered_checks()
    record = _record()
    path = tmp_path / "baseline.yaml"
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")

    assert chk.run([tmp_path]).ok

    record["content_digest"] = "0" * 64
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")

    result = chk.run([tmp_path])
    assert any(error.code == chk.CODE_CONTENT_DIGEST for error in result.errors)
