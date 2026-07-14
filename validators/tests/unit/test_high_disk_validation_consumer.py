"""Hermetic tests for the fixed-purpose high-disk validation file drop."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from creator_engine_validator.high_disk_validation_consumer import (
    AtomicFileDropHighDiskValidationConsumer,
    HighDiskValidationConsumerError,
)
from creator_engine_validator.high_disk_validation_lane import HighDiskValidationSubmission
from creator_engine_validator.validation_sandbox_receipt import ValidationSandboxReceiptIssuer


SHA = "a" * 40
HEAD = "b" * 40
TREE = "c" * 40
POLICY = "d" * 64
IMAGE = "sha256:" + "e" * 64
DIGEST = "f" * 64


def _submission(**changes: object) -> HighDiskValidationSubmission:
    values: dict[str, object] = {
        "repository": "creator-engine/creator-engine",
        "base_sha": SHA,
        "head_sha": HEAD,
        "expected_tree_sha": TREE,
        "sorted_carrier_digest": DIGEST,
        "validator_command": ("ce", "validate-pr", "--base", SHA),
        "validator_profile": "default",
        "policy_digest": POLICY,
        "image_digest": IMAGE,
        "minimum_headroom_gib": 30.0,
        "venue_id": "dgx-validation-lane",
    }
    values.update(changes)
    return HighDiskValidationSubmission(**values)


def _result_bytes(submission: HighDiskValidationSubmission, request_id: str, **changes: object) -> bytes:
    issuer = ValidationSandboxReceiptIssuer(
        secret=b"test-receipt-secret",
        clock=lambda: datetime(2026, 7, 14, tzinfo=UTC),
    )
    receipt = issuer.mint(
        tree_sha=submission.expected_tree_sha,
        command=submission.validator_command,
        policy_sha=submission.policy_digest,
        image_sha=submission.image_digest,
        mount_manifest_applied=(),
        egress_allowlist_applied=(),
        secret_allowlist_applied=(),
        returncode=0,
    )
    receipt_bytes = json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    success: dict[str, object] = {
        "repository": submission.repository,
        "base_sha": submission.base_sha,
        "head_sha": submission.head_sha,
        "tree_sha": submission.expected_tree_sha,
        "sorted_carrier_digest": submission.sorted_carrier_digest,
        "validator_command": list(submission.validator_command),
        "validator_profile": submission.validator_profile,
        "policy_digest": submission.policy_digest,
        "image_digest": submission.image_digest,
        "minimum_headroom_gib": submission.minimum_headroom_gib,
        "venue_id": submission.venue_id,
        "allocation_id": "allocation-1",
        "receipt_bytes_b64": base64.b64encode(receipt_bytes).decode("ascii"),
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
    }
    success.update(changes)
    return json.dumps(
        {
            "kind": "high-disk-validation-result",
            "schema_version": "1",
            "request_id": request_id,
            "status": "verified-success",
            "success": success,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _drop_root(tmp_path: Path) -> Path:
    root = tmp_path / "drop"
    (root / "incoming").mkdir(parents=True)
    (root / "results").mkdir()
    return root


def test_writes_canonical_credential_free_submission_and_bundle(tmp_path: Path, monkeypatch) -> None:
    root = _drop_root(tmp_path)
    request_id = "1" * 32
    submission = _submission()
    (root / "results" / f"{request_id}.json").write_bytes(_result_bytes(submission, request_id))
    monkeypatch.setenv("GH_TOKEN", "github-token-must-not-cross-the-drop")
    monkeypatch.setenv("OPENBAO_TOKEN", "vault-token-must-not-cross-the-drop")

    result = AtomicFileDropHighDiskValidationConsumer(
        root,
        request_id_factory=lambda: request_id,
    ).submit(submission)

    request = root / "incoming" / request_id
    submission_bytes = (request / "submission.json").read_bytes()
    bundle = json.loads((request / "bundle.json").read_text(encoding="utf-8"))
    payload = json.loads(submission_bytes.decode("utf-8"))
    assert result.tree_sha == TREE
    assert payload["kind"] == "high-disk-validation-submission"
    assert payload["submission"]["validator_command"] == ["ce", "validate-pr", "--base", SHA]
    assert bundle["submission_sha256"] == hashlib.sha256(submission_bytes).hexdigest()
    assert b"github-token-must-not-cross-the-drop" not in submission_bytes
    assert b"vault-token-must-not-cross-the-drop" not in submission_bytes
    assert "GH_TOKEN" not in submission_bytes.decode("utf-8")


def test_refuses_binding_mismatch_from_file_drop(tmp_path: Path) -> None:
    root = _drop_root(tmp_path)
    request_id = "2" * 32
    submission = _submission()
    (root / "results" / f"{request_id}.json").write_bytes(
        _result_bytes(submission, request_id, base_sha="0" * 40)
    )

    with pytest.raises(HighDiskValidationConsumerError, match="base_sha"):
        AtomicFileDropHighDiskValidationConsumer(root, request_id_factory=lambda: request_id).submit(submission)


def test_refuses_failed_remote_execution(tmp_path: Path) -> None:
    root = _drop_root(tmp_path)
    request_id = "5" * 32
    submission = _submission()
    result = json.loads(_result_bytes(submission, request_id).decode("utf-8"))
    result["status"] = "failed"
    (root / "results" / f"{request_id}.json").write_text(json.dumps(result), encoding="utf-8")

    with pytest.raises(HighDiskValidationConsumerError, match="verified success"):
        AtomicFileDropHighDiskValidationConsumer(root, request_id_factory=lambda: request_id).submit(submission)


def test_refuses_bad_receipt_binding(tmp_path: Path) -> None:
    root = _drop_root(tmp_path)
    request_id = "6" * 32
    submission = _submission()
    result = json.loads(_result_bytes(submission, request_id).decode("utf-8"))
    receipt = json.loads(base64.b64decode(result["success"]["receipt_bytes_b64"]))
    receipt["tree_sha"] = "0" * 40
    receipt_bytes = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    result["success"]["receipt_bytes_b64"] = base64.b64encode(receipt_bytes).decode("ascii")
    result["success"]["receipt_sha256"] = hashlib.sha256(receipt_bytes).hexdigest()
    (root / "results" / f"{request_id}.json").write_text(json.dumps(result), encoding="utf-8")

    with pytest.raises(HighDiskValidationConsumerError, match="receipt tree_sha"):
        AtomicFileDropHighDiskValidationConsumer(root, request_id_factory=lambda: request_id).submit(submission)


def test_refuses_unavailable_drop_directories(tmp_path: Path) -> None:
    with pytest.raises(HighDiskValidationConsumerError, match="incoming drop directory is unavailable"):
        AtomicFileDropHighDiskValidationConsumer(tmp_path / "absent").submit(_submission())


def test_refuses_timeout_without_a_result(tmp_path: Path) -> None:
    root = _drop_root(tmp_path)
    now = [0.0]

    with pytest.raises(HighDiskValidationConsumerError, match="did not return a result before timeout"):
        AtomicFileDropHighDiskValidationConsumer(
            root,
            timeout_seconds=0.2,
            poll_interval_seconds=0.1,
            request_id_factory=lambda: "3" * 32,
            clock=lambda: now[0],
            sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds),
        ).submit(_submission())


def test_refuses_credential_like_command_before_writing_request(tmp_path: Path) -> None:
    root = _drop_root(tmp_path)
    submission = _submission(validator_command=("ce", "validate-pr", "--token", "not-allowed"))

    with pytest.raises(HighDiskValidationConsumerError, match="credential-like"):
        AtomicFileDropHighDiskValidationConsumer(
            root,
            request_id_factory=lambda: "4" * 32,
        ).submit(submission)

    assert not list((root / "incoming").iterdir())
