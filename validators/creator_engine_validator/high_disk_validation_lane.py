"""Fail-closed, injected adapter for high-disk validation candidates.

This module deliberately owns no transport, daemon, or container runtime.  It
binds the existing daemon-allocation and validation-sandbox seams so a caller
can prove that one immutable candidate was materialized and validated without
substituting an ambient ref or accepting a partial result.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .disk_headroom import DEFAULT_MIN_FREE_GB, check_headroom
from .forge.daemon_allocation import (
    DaemonPathAllocation,
    DaemonPathAllocator,
    DaemonPathReceipt,
)
from .validation_sandbox import ValidationSandboxSpec
from .validation_sandbox_receipt import (
    ValidationSandboxReceipt,
    ValidationSandboxReceiptIssuer,
    command_sha256,
)
from .validation_sandbox_runner import (
    ValidationSandboxContainerRun,
    run_validation_sandbox_in_container,
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
_VENUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_DEFAULT_PROFILE = "default"


class HighDiskValidationLaneError(ValueError):
    """The candidate cannot be safely materialized or consumed."""


@dataclass(frozen=True)
class HighDiskValidationSubmission:
    """Immutable, secret-free identity of exactly one validation candidate."""

    repository: str
    base_sha: str
    head_sha: str
    expected_tree_sha: str
    sorted_carrier_digest: str
    validator_command: tuple[str, ...]
    validator_profile: str
    policy_digest: str
    image_digest: str
    minimum_headroom_gib: float
    venue_id: str

    def __post_init__(self) -> None:
        for field_name in ("base_sha", "head_sha", "expected_tree_sha"):
            _require_sha(field_name, getattr(self, field_name))
        _require_digest("sorted_carrier_digest", self.sorted_carrier_digest)
        _require_digest("policy_digest", self.policy_digest)
        if not _REPOSITORY_RE.fullmatch(self.repository):
            raise HighDiskValidationLaneError("repository must be a canonical owner/name identity")
        if not _VENUE_RE.fullmatch(self.venue_id):
            raise HighDiskValidationLaneError("venue_id must be a non-path identifier")
        if self.minimum_headroom_gib < DEFAULT_MIN_FREE_GB:
            raise HighDiskValidationLaneError(
                f"minimum_headroom_gib must be at least {DEFAULT_MIN_FREE_GB:g}"
            )
        command = tuple(str(value) for value in self.validator_command)
        if len(command) < 2 or command[:2] != ("ce", "validate-pr"):
            raise HighDiskValidationLaneError("validator_command must use ce validate-pr semantics")
        if self.validator_profile != _DEFAULT_PROFILE:
            raise HighDiskValidationLaneError("validator_profile must be the default full preflight profile")
        if not self.image_digest.startswith("sha256:") or not _DIGEST_RE.fullmatch(self.image_digest[7:]):
            raise HighDiskValidationLaneError("image_digest must be a sha256 image digest")
        object.__setattr__(self, "validator_command", command)


@dataclass(frozen=True)
class MaterializationEvidence:
    """Injected CAS boundary result; it must attest one atomic materialization."""

    repository: str
    base_sha: str
    head_sha: str
    tree_sha: str
    atomic: bool


@dataclass(frozen=True)
class HighDiskValidationSuccess:
    """Immutable, secret-free result suitable for a later #1008 consumer."""

    repository: str
    base_sha: str
    head_sha: str
    tree_sha: str
    sorted_carrier_digest: str
    validator_command: tuple[str, ...]
    validator_profile: str
    policy_digest: str
    image_digest: str
    minimum_headroom_gib: float
    venue_id: str
    allocation_id: str
    receipt_bytes: bytes
    receipt_sha256: str


Materializer = Callable[[HighDiskValidationSubmission, DaemonPathAllocation], MaterializationEvidence]
HeadroomProbe = Callable[[Path, float], float]
SandboxRunner = Callable[..., ValidationSandboxContainerRun]


def _require_sha(field_name: str, value: str) -> None:
    if not _SHA_RE.fullmatch(value):
        raise HighDiskValidationLaneError(f"{field_name} must be a lowercase full 40-hex SHA")


def _require_digest(field_name: str, value: str) -> None:
    if not _DIGEST_RE.fullmatch(value):
        raise HighDiskValidationLaneError(f"{field_name} must be lowercase 64-hex")


def _default_headroom_probe(path: Path, minimum: float) -> float:
    return check_headroom(path, min_free_gb=minimum)


def _require_allocation_binding(
    submission: HighDiskValidationSubmission,
    allocation: DaemonPathAllocation,
) -> Path:
    if allocation.repo != submission.repository:
        raise HighDiskValidationLaneError("allocation repository does not match submission")
    if allocation.base_sha != submission.base_sha or allocation.head_sha != submission.head_sha:
        raise HighDiskValidationLaneError("allocation base/head does not match submission")
    if allocation.worktree_path is None or not allocation.worktree_path.is_absolute():
        raise HighDiskValidationLaneError("allocation requires an absolute daemon-owned worktree path")
    return allocation.worktree_path


def _require_materialization(
    evidence: MaterializationEvidence, submission: HighDiskValidationSubmission
) -> None:
    if not evidence.atomic:
        raise HighDiskValidationLaneError("materialization evidence is not atomic")
    if (
        evidence.repository != submission.repository
        or evidence.base_sha != submission.base_sha
        or evidence.head_sha != submission.head_sha
        or evidence.tree_sha != submission.expected_tree_sha
    ):
        raise HighDiskValidationLaneError("materialization evidence does not bind the submitted repository/base/head/tree")


def _receipt_bytes(receipt: ValidationSandboxReceipt) -> bytes:
    return json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")


def _require_receipt_binding(
    receipt: ValidationSandboxReceipt | None,
    *,
    submission: HighDiskValidationSubmission,
    issuer: ValidationSandboxReceiptIssuer,
) -> ValidationSandboxReceipt:
    if receipt is None:
        raise HighDiskValidationLaneError("validation returned no signed receipt")
    if not issuer.verify(receipt):
        raise HighDiskValidationLaneError("validation receipt signature is invalid")
    if receipt.returncode != 0:
        raise HighDiskValidationLaneError("validation receipt records a nonzero return code")
    expected = {
        "tree_sha": submission.expected_tree_sha,
        "command_sha256": command_sha256(submission.validator_command),
        "policy_sha": submission.policy_digest,
        "image_sha": submission.image_digest,
    }
    for field_name, value in expected.items():
        if getattr(receipt, field_name) != value:
            raise HighDiskValidationLaneError(f"validation receipt {field_name} does not match submission")
    return receipt


def validate_high_disk_submission(
    submission: HighDiskValidationSubmission,
    *,
    allocator: DaemonPathAllocator,
    allocation: DaemonPathAllocation,
    allocation_receipt: DaemonPathReceipt,
    materialize: Materializer,
    validation_spec: ValidationSandboxSpec,
    receipt_issuer: ValidationSandboxReceiptIssuer,
    sandbox_runner: SandboxRunner = run_validation_sandbox_in_container,
    headroom_probe: HeadroomProbe = _default_headroom_probe,
) -> HighDiskValidationSuccess:
    """Validate one CAS-materialized submission, refusing every unbound result.

    ``materialize`` is the intentionally injected remote-CAS protocol boundary.
    This adapter never discovers refs, allocates a lane, or performs transport.
    """

    if not isinstance(submission, HighDiskValidationSubmission):
        raise TypeError("submission must be HighDiskValidationSubmission")
    verified = allocator.verify_receipt(allocation_receipt, allocation)
    if verified != allocation:
        raise HighDiskValidationLaneError("allocation receipt did not return the supplied allocation")
    worktree_path = _require_allocation_binding(submission, allocation)
    if validation_spec.cwd != worktree_path:
        raise HighDiskValidationLaneError("validation spec cwd does not match allocation worktree path")
    if tuple(validation_spec.command) != submission.validator_command:
        raise HighDiskValidationLaneError("validation spec command does not match submission")
    measured_headroom = headroom_probe(worktree_path, submission.minimum_headroom_gib)
    if measured_headroom < submission.minimum_headroom_gib:
        raise HighDiskValidationLaneError("venue headroom is insufficient for submission")

    evidence = materialize(submission, allocation)
    _require_materialization(evidence, submission)
    container_run = sandbox_runner(
        validation_spec,
        tree_sha=submission.expected_tree_sha,
        receipt_issuer=receipt_issuer,
    )
    if container_run.result.returncode != 0:
        raise HighDiskValidationLaneError("validation returned a nonzero result")
    receipt = _require_receipt_binding(
        container_run.receipt,
        submission=submission,
        issuer=receipt_issuer,
    )
    receipt_bytes = _receipt_bytes(receipt)
    return HighDiskValidationSuccess(
        repository=submission.repository,
        base_sha=submission.base_sha,
        head_sha=submission.head_sha,
        tree_sha=submission.expected_tree_sha,
        sorted_carrier_digest=submission.sorted_carrier_digest,
        validator_command=submission.validator_command,
        validator_profile=submission.validator_profile,
        policy_digest=submission.policy_digest,
        image_digest=submission.image_digest,
        minimum_headroom_gib=submission.minimum_headroom_gib,
        venue_id=submission.venue_id,
        allocation_id=allocation.allocation_id,
        receipt_bytes=receipt_bytes,
        receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
    )


__all__ = [
    "HighDiskValidationLaneError",
    "HighDiskValidationSubmission",
    "HighDiskValidationSuccess",
    "MaterializationEvidence",
    "validate_high_disk_submission",
]
