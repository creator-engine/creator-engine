from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from creator_engine_validator.forge.daemon_allocation import (
    DaemonPathAllocator,
    DaemonPathReceipt,
    DaemonReceiptError,
    DaemonRootError,
    DaemonRuntimeRoots,
)


def _roots(tmp_path: Path) -> DaemonRuntimeRoots:
    return DaemonRuntimeRoots.from_root(tmp_path / "runtime", create=True)


def test_allocation_issuance_uses_unique_randomized_directories(tmp_path: Path) -> None:
    allocator = DaemonPathAllocator(_roots(tmp_path))

    first, first_receipt = allocator.allocate_conveyor_paths(
        repo="creator-engine/creator-engine",
        branch_name="feature/alloc",
        pr_number=410,
        base_sha="a" * 40,
        head_sha="b" * 40,
    )
    second, second_receipt = allocator.allocate_conveyor_paths(
        repo="creator-engine/creator-engine",
        branch_name="feature/alloc",
        pr_number=410,
        base_sha="a" * 40,
        head_sha="b" * 40,
    )

    assert first.allocation_id != second.allocation_id
    assert first.nonce != second.nonce
    assert first_receipt != second_receipt
    assert first.repo_path != second.repo_path
    assert first.worktree_path != second.worktree_path
    assert first.bundle_path != second.bundle_path
    assert first.repo_path is not None and first.repo_path.is_dir()
    assert first.worktree_path is not None and first.worktree_path.is_dir()
    assert first.bundle_path is not None and first.bundle_path.is_dir()
    assert second.repo_path is not None and second.repo_path.is_dir()
    assert second.worktree_path is not None and second.worktree_path.is_dir()
    assert second.bundle_path is not None and second.bundle_path.is_dir()


def test_receipt_verification_succeeds_for_allocator_issued_receipt(tmp_path: Path) -> None:
    allocator = DaemonPathAllocator(_roots(tmp_path))
    allocation, receipt = allocator.allocate_integrator_workspace(
        repo="creator-engine/creator-engine",
        pr_number=410,
        head_sha="c" * 40,
    )

    assert allocator.verify_receipt(receipt) == allocation
    assert allocator.verify_receipt(receipt, allocation) == allocation
    assert allocation.workspace_path is not None
    assert allocation.to_audit_record(allocator.roots)["paths"] == {
        "workspace_path": allocation.workspace_path.name
    }


def test_hand_constructed_receipt_not_issued_by_allocator_is_rejected(tmp_path: Path) -> None:
    allocator = DaemonPathAllocator(_roots(tmp_path))
    forged = DaemonPathReceipt(
        allocation_id="not-issued",
        nonce="not-issued",
        signature="not-issued",
    )

    with pytest.raises(DaemonReceiptError):
        allocator.verify_receipt(forged)


def test_receipt_from_another_allocator_instance_is_rejected(tmp_path: Path) -> None:
    roots = _roots(tmp_path)
    issuer = DaemonPathAllocator(roots)
    verifier = DaemonPathAllocator(roots)
    _allocation, receipt = issuer.allocate_integrator_workspace(
        repo="creator-engine/creator-engine",
        pr_number=410,
        head_sha="d" * 40,
    )

    with pytest.raises(DaemonReceiptError):
        verifier.verify_receipt(receipt)


def test_allocation_outside_runtime_root_is_rejected_even_with_valid_receipt(tmp_path: Path) -> None:
    allocator = DaemonPathAllocator(_roots(tmp_path))
    allocation, receipt = allocator.allocate_integrator_workspace(
        repo="creator-engine/creator-engine",
        pr_number=410,
        head_sha="e" * 40,
    )
    outside = tmp_path / "outside-workspace"
    outside.mkdir()

    escaped = replace(allocation, workspace_path=outside)

    with pytest.raises(DaemonRootError):
        allocator.verify_receipt(receipt, escaped)


def test_cleanup_is_receipt_guarded_and_idempotent(tmp_path: Path) -> None:
    allocator = DaemonPathAllocator(_roots(tmp_path))
    allocation, receipt = allocator.allocate_integrator_workspace(
        repo="creator-engine/creator-engine",
        pr_number=410,
        head_sha="f" * 40,
    )
    workspace = allocation.workspace_path
    assert workspace is not None and workspace.is_dir()

    assert allocator.cleanup(receipt) is True
    assert not workspace.exists()
    assert allocator.cleanup(receipt) is False
    with pytest.raises(DaemonReceiptError):
        allocator.verify_receipt(receipt)

    forged = DaemonPathReceipt(
        allocation_id=receipt.allocation_id,
        nonce=receipt.nonce,
        signature="not-the-issued-signature",
    )
    with pytest.raises(DaemonReceiptError):
        allocator.cleanup(forged)
