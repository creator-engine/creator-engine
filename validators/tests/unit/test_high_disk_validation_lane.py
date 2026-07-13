"""Hermetic contract tests for the high-disk validation lane adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from creator_engine_validator.forge.authority_contexts import ValidationSandboxContext
from creator_engine_validator.forge.daemon_allocation import (
    DaemonPathAllocation,
    DaemonPathReceipt,
)
from creator_engine_validator.high_disk_validation_lane import (
    HighDiskValidationLaneError,
    HighDiskValidationSubmission,
    MaterializationEvidence,
    validate_high_disk_submission,
)
from creator_engine_validator.validation_sandbox import ValidationSandboxResult, ValidationSandboxSpec
from creator_engine_validator.validation_sandbox_receipt import ValidationSandboxReceiptIssuer
from creator_engine_validator.validation_sandbox_runner import ValidationSandboxContainerRun


SHA = "a" * 40
HEAD = "b" * 40
TREE = "c" * 40
DIGEST = "d" * 64
POLICY = "e" * 64
IMAGE = "sha256:" + "f" * 64
NOW = datetime(2026, 7, 13, tzinfo=UTC)


class Allocator:
    def __init__(self, allocation: DaemonPathAllocation) -> None:
        self.allocation = allocation
        self.calls = 0

    def verify_receipt(
        self, receipt: DaemonPathReceipt, allocation: DaemonPathAllocation
    ) -> DaemonPathAllocation:
        self.calls += 1
        assert receipt.allocation_id == allocation.allocation_id
        assert allocation == self.allocation
        return allocation


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
        "venue_id": "validation-lane-a",
    }
    values.update(changes)
    return HighDiskValidationSubmission(**values)


def _allocation(tmp_path: Path, **changes: object) -> DaemonPathAllocation:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    values: dict[str, object] = {
        "allocation_id": "allocation-1",
        "nonce": "nonce-1",
        "created_at": NOW,
        "repo": "creator-engine/creator-engine",
        "branch_name": "candidate",
        "base_sha": SHA,
        "head_sha": HEAD,
        "worktree_path": worktree,
        "root_provenance": (("worktree_path", "worktree"),),
    }
    values.update(changes)
    return DaemonPathAllocation(**values)


def _spec(tmp_path: Path, allocation: DaemonPathAllocation) -> ValidationSandboxSpec:
    context = ValidationSandboxContext.from_sandbox(tmp_path / "sandbox")
    return ValidationSandboxSpec(
        context=context,
        command=("ce", "validate-pr", "--base", SHA),
        cwd=allocation.worktree_path,
        timeout_seconds=30,
        env=context.env,
    )


def _issuer() -> ValidationSandboxReceiptIssuer:
    return ValidationSandboxReceiptIssuer(
        secret=b"unit-test-only",
        clock=lambda: NOW,
        nonce_factory=lambda: "receipt-nonce",
    )


def _run(
    tmp_path: Path,
    *,
    submission: HighDiskValidationSubmission | None = None,
    allocation: DaemonPathAllocation | None = None,
    headroom: float = 30.0,
    evidence: MaterializationEvidence | None = None,
    returncode: int = 0,
    receipt_tree: str | None = None,
    receipt_command: tuple[str, ...] | None = None,
    receipt_policy: str | None = None,
    receipt_image: str | None = None,
):
    allocation = allocation or _allocation(tmp_path)
    submission = submission or _submission()
    spec = _spec(tmp_path, allocation)
    issuer = _issuer()
    calls = {"materialize": 0, "runner": 0}

    def materialize(
        candidate: HighDiskValidationSubmission, received: DaemonPathAllocation
    ) -> MaterializationEvidence:
        calls["materialize"] += 1
        assert candidate == submission
        assert received == allocation
        return evidence or MaterializationEvidence(
            repository=candidate.repository,
            base_sha=candidate.base_sha,
            head_sha=candidate.head_sha,
            tree_sha=candidate.expected_tree_sha,
            atomic=True,
        )

    def runner(
        observed_spec: ValidationSandboxSpec,
        *,
        tree_sha: str,
        receipt_issuer: ValidationSandboxReceiptIssuer,
    ) -> ValidationSandboxContainerRun:
        calls["runner"] += 1
        receipt = receipt_issuer.mint(
            tree_sha=receipt_tree or tree_sha,
            command=receipt_command or tuple(observed_spec.command),
            policy_sha=receipt_policy or POLICY,
            image_sha=receipt_image or IMAGE,
            mount_manifest_applied=(),
            egress_allowlist_applied=(),
            secret_allowlist_applied=(),
            returncode=returncode,
            issued_at=NOW,
        )
        return ValidationSandboxContainerRun(
            result=ValidationSandboxResult(returncode, "", "", 0.01, observed_spec),
            receipt=receipt,
        )

    result = validate_high_disk_submission(
        submission,
        allocator=Allocator(allocation),
        allocation=allocation,
        allocation_receipt=DaemonPathReceipt("allocation-1", "nonce-1", "receipt"),
        materialize=materialize,
        validation_spec=spec,
        receipt_issuer=issuer,
        sandbox_runner=runner,
        headroom_probe=lambda _path, _minimum: headroom,
    )
    return result, calls


def test_success_binds_atomic_materialization_and_exact_signed_receipt(tmp_path: Path) -> None:
    result, calls = _run(tmp_path)

    assert calls == {"materialize": 1, "runner": 1}
    assert result.repository == "creator-engine/creator-engine"
    assert result.tree_sha == TREE
    assert result.receipt_sha256
    assert result.receipt_bytes.startswith(b'{"command_sha256"')
    assert "unit-test-only" not in repr(result)


@pytest.mark.parametrize(
    ("changes", "needle"),
    [
        ({"base_sha": "short"}, "base_sha"),
        ({"repository": "../unsafe"}, "repository"),
        ({"venue_id": "venue/unsafe"}, "venue_id"),
        ({"minimum_headroom_gib": 29.9}, "minimum_headroom_gib"),
    ],
)
def test_malformed_submission_refuses_before_materialization(
    tmp_path: Path, changes: dict[str, object], needle: str
) -> None:
    with pytest.raises(HighDiskValidationLaneError, match=needle):
        _run(tmp_path, submission=_submission(**changes))


def test_insufficient_disk_refuses_before_materialization(tmp_path: Path) -> None:
    with pytest.raises(HighDiskValidationLaneError, match="headroom"):
        _run(tmp_path, headroom=29.9)


@pytest.mark.parametrize(
    "evidence",
    [
        MaterializationEvidence("creator-engine/creator-engine", SHA, HEAD, TREE, False),
        MaterializationEvidence("creator-engine/creator-engine", SHA, HEAD, "0" * 40, True),
        MaterializationEvidence("other/repository", SHA, HEAD, TREE, True),
    ],
)
def test_cas_materialization_mismatch_refuses_before_runner(
    tmp_path: Path, evidence: MaterializationEvidence
) -> None:
    with pytest.raises(HighDiskValidationLaneError, match="materialization"):
        _run(tmp_path, evidence=evidence)


def test_nonzero_validation_refuses_receipt(tmp_path: Path) -> None:
    with pytest.raises(HighDiskValidationLaneError, match="nonzero"):
        _run(tmp_path, returncode=1)


@pytest.mark.parametrize(
    ("changes", "run_changes", "needle"),
    [
        ({}, {"receipt_tree": "0" * 40}, "tree_sha"),
        ({}, {"receipt_command": ("ce", "validate-pr", "--wrong")}, "command_sha256"),
        ({}, {"receipt_policy": "0" * 64}, "policy_sha"),
        ({"image_digest": "sha256:" + "0" * 64}, {}, "image_sha"),
    ],
)
def test_receipt_binding_mismatch_refuses(
    tmp_path: Path,
    changes: dict[str, object],
    run_changes: dict[str, object],
    needle: str,
) -> None:
    with pytest.raises(HighDiskValidationLaneError, match=needle):
        _run(tmp_path, submission=_submission(**changes), **run_changes)


def test_allocation_binding_mismatch_refuses_before_materialization(tmp_path: Path) -> None:
    allocation = _allocation(tmp_path, head_sha="1" * 40)
    with pytest.raises(HighDiskValidationLaneError, match="allocation"):
        _run(tmp_path, allocation=allocation)
