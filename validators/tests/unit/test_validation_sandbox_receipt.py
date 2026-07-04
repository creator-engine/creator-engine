from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

from creator_engine_validator.validation_sandbox_receipt import ValidationSandboxReceiptIssuer


TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
POLICY_SHA = "a" * 64
IMAGE_SHA = "sha256:" + "b" * 64


def _issuer(now: datetime, *, ttl_seconds: int = 60) -> ValidationSandboxReceiptIssuer:
    return ValidationSandboxReceiptIssuer(
        secret=b"test-secret",
        nonce_factory=lambda: "nonce-001",
        clock=lambda: now,
        ttl_seconds=ttl_seconds,
    )


def _mint(now: datetime):
    return _issuer(now).mint(
        tree_sha=TREE_SHA,
        command=("ce", "validate-pr", "--offline"),
        policy_sha=POLICY_SHA,
        image_sha=IMAGE_SHA,
        mount_manifest_applied=({"path": "/workspace", "mode": "ro"},),
        egress_allowlist_applied=(),
        secret_allowlist_applied=(),
        returncode=0,
    )


def test_issued_at_is_hmac_covered():
    now = datetime(2026, 7, 4, 12, 0, 0, tzinfo=UTC)
    issuer = _issuer(now)
    receipt = _mint(now)

    assert issuer.verify(receipt)
    tampered = dataclasses.replace(receipt, issued_at="2026-07-04T12:00:01Z")
    assert not issuer.verify(tampered)


def test_stale_receipt_is_rejected():
    issued = datetime(2026, 7, 4, 12, 0, 0, tzinfo=UTC)
    receipt = _mint(issued)

    assert _issuer(issued + timedelta(seconds=60), ttl_seconds=60).verify(receipt)
    assert not _issuer(issued + timedelta(seconds=61), ttl_seconds=60).verify(receipt)
