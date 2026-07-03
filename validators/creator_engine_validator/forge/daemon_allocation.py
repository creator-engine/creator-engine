"""Daemon-owned path allocation and receipt verification.

This module is intentionally standalone: later CE-410 slices wire it into the
conveyor daemon and integrator belt.  The allocator issues randomized
directories under daemon-private runtime roots and returns an in-process
receipt that can be verified only by the issuing allocator instance.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import stat
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class DaemonAllocationError(Exception):
    """Base class for daemon path allocation failures."""


class DaemonRootError(DaemonAllocationError):
    """A configured root or allocated path failed runtime-root confinement."""


class DaemonReceiptError(DaemonAllocationError):
    """A daemon path receipt was not issued by this allocator or is stale."""


_ROOT_FIELDS = ("runtime_root", "repo_root", "worktree_root", "bundle_root", "workspace_root")
_PATH_FIELDS = ("repo_path", "worktree_path", "bundle_path", "workspace_path")
_PATH_ROOT_DEFAULTS = {
    "repo_path": "repo",
    "worktree_path": "worktree",
    "bundle_path": "bundle",
    "workspace_path": "workspace",
}
_SAFE_PREFIX_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _safe_label(value: object, *, fallback: str = "alloc") -> str:
    label = _SAFE_PREFIX_RE.sub("-", str(value)).strip(".-")
    if not label:
        label = fallback
    return label[:48]


def _now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class DaemonRuntimeRoots:
    """Resolved daemon-private roots used for path allocation.

    Roots must already exist unless created through :meth:`from_root`.  Each
    root is resolved, owned by the daemon user, not group/world-writable, and
    every typed allocation root is confined under ``runtime_root``.
    """

    runtime_root: Path
    repo_root: Path
    worktree_root: Path
    bundle_root: Path
    workspace_root: Path
    owner_uid: int | None = None

    def __post_init__(self) -> None:
        expected_uid = os.geteuid() if self.owner_uid is None and hasattr(os, "geteuid") else self.owner_uid
        resolved: dict[str, Path] = {}
        for field_name in _ROOT_FIELDS:
            raw_path = Path(getattr(self, field_name))
            if not raw_path.is_absolute():
                raise DaemonRootError(f"{field_name} must be absolute: {raw_path}")
            try:
                root = raw_path.resolve(strict=True)
            except FileNotFoundError as exc:
                raise DaemonRootError(f"{field_name} does not exist: {raw_path}") from exc
            if not root.is_dir():
                raise DaemonRootError(f"{field_name} is not a directory: {root}")
            info = root.stat()
            if expected_uid is not None and info.st_uid != expected_uid:
                raise DaemonRootError(f"{field_name} is not owned by uid {expected_uid}: {root}")
            if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise DaemonRootError(f"{field_name} is group/world-writable: {root}")
            resolved[field_name] = root

        runtime_root = resolved["runtime_root"]
        for field_name, root in resolved.items():
            if field_name != "runtime_root" and not _is_relative_to(root, runtime_root):
                raise DaemonRootError(f"{field_name} escapes runtime_root: {root}")
            object.__setattr__(self, field_name, root)
        object.__setattr__(self, "owner_uid", expected_uid)

    @classmethod
    def from_root(cls, runtime_root: str | Path, *, create: bool = False) -> "DaemonRuntimeRoots":
        """Build the standard typed root layout under one runtime root."""

        root = Path(runtime_root)
        if not root.is_absolute():
            raise DaemonRootError(f"runtime_root must be absolute: {root}")
        if create:
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            root.chmod(0o700)
            for child_name in ("repos", "worktrees", "bundles", "workspaces"):
                child = root / child_name
                child.mkdir(mode=0o700, exist_ok=True)
                child.chmod(0o700)
        return cls(
            runtime_root=root,
            repo_root=root / "repos",
            worktree_root=root / "worktrees",
            bundle_root=root / "bundles",
            workspace_root=root / "workspaces",
        )

    def root_for(self, kind: str) -> Path:
        """Return the configured root for an allocation kind."""

        if kind == "runtime":
            return self.runtime_root
        if kind == "repo":
            return self.repo_root
        if kind == "worktree":
            return self.worktree_root
        if kind == "bundle":
            return self.bundle_root
        if kind == "workspace":
            return self.workspace_root
        raise DaemonRootError(f"unknown daemon allocation root kind: {kind}")

    def confine_path(self, path: str | Path, kind: str) -> Path:
        """Resolve ``path`` and require it to stay under the named root."""

        root = self.root_for(kind)
        candidate = Path(path)
        if not candidate.is_absolute():
            raise DaemonRootError(f"allocated path for {kind} must be absolute: {candidate}")
        resolved = candidate.resolve(strict=False)
        if not _is_relative_to(resolved, root):
            raise DaemonRootError(f"allocated path for {kind} escapes daemon runtime root: {resolved}")
        return resolved

    def to_audit_record(self) -> dict[str, str]:
        """Return a secret-free root summary for audit evidence."""

        return {
            "runtime_root": str(self.runtime_root),
            "repo_root": str(self.repo_root.relative_to(self.runtime_root)),
            "worktree_root": str(self.worktree_root.relative_to(self.runtime_root)),
            "bundle_root": str(self.bundle_root.relative_to(self.runtime_root)),
            "workspace_root": str(self.workspace_root.relative_to(self.runtime_root)),
        }


@dataclass(frozen=True)
class DaemonPathAllocation:
    """Value object describing daemon-issued paths and their provenance."""

    allocation_id: str
    nonce: str
    created_at: datetime
    repo: str
    branch_name: str | None = None
    pr_number: int | None = None
    base_sha: str | None = None
    head_sha: str | None = None
    repo_path: Path | None = None
    worktree_path: Path | None = None
    bundle_path: Path | None = None
    workspace_path: Path | None = None
    root_provenance: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.allocation_id:
            raise ValueError("allocation_id is required")
        if not self.nonce:
            raise ValueError("nonce is required")
        if not self.repo:
            raise ValueError("repo is required")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        for field_name in _PATH_FIELDS:
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, Path(value))
        object.__setattr__(self, "root_provenance", tuple(sorted(self.root_provenance)))

    def iter_paths(self) -> Iterator[tuple[str, str, Path]]:
        """Yield ``(field_name, root_kind, path)`` for present allocated paths."""

        provenance = dict(self.root_provenance)
        for field_name in _PATH_FIELDS:
            path = getattr(self, field_name)
            if path is None:
                continue
            yield field_name, provenance.get(field_name, _PATH_ROOT_DEFAULTS[field_name]), path

    def to_audit_record(self, roots: DaemonRuntimeRoots) -> dict[str, Any]:
        """Return a secret-free allocation record; nonce/signature are omitted."""

        paths: dict[str, str] = {}
        for field_name, kind, path in self.iter_paths():
            confined = roots.confine_path(path, kind)
            paths[field_name] = str(confined.relative_to(roots.root_for(kind)))
        return {
            "allocation_id": self.allocation_id,
            "repo": self.repo,
            "branch_name": self.branch_name,
            "pr_number": self.pr_number,
            "base_sha": self.base_sha,
            "head_sha": self.head_sha,
            "created_at": self.created_at.isoformat(),
            "paths": paths,
            "root_provenance": dict(self.root_provenance),
        }


@dataclass(frozen=True)
class DaemonPathReceipt:
    """Opaque bearer receipt bound to one daemon-issued allocation."""

    allocation_id: str
    nonce: str
    signature: str


class DaemonPathAllocator:
    """Issue and verify daemon-owned path allocations."""

    def __init__(
        self,
        roots: DaemonRuntimeRoots,
        *,
        secret: bytes | None = None,
        clock: Callable[[], datetime] | None = None,
        allocation_id_factory: Callable[[], str] | None = None,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        self._roots = roots
        self._secret = secret if secret is not None else secrets.token_bytes(32)
        self._clock = clock or _now_utc
        self._allocation_id_factory = allocation_id_factory or (lambda: secrets.token_urlsafe(18))
        self._nonce_factory = nonce_factory or (lambda: secrets.token_urlsafe(32))
        self._allocations: dict[str, DaemonPathAllocation] = {}
        self._signatures: dict[str, str] = {}
        self._cleaned: set[str] = set()

    @property
    def roots(self) -> DaemonRuntimeRoots:
        return self._roots

    def allocate_conveyor_paths(
        self,
        *,
        repo: str,
        branch_name: str,
        pr_number: int | None = None,
        base_sha: str | None = None,
        head_sha: str | None = None,
    ) -> tuple[DaemonPathAllocation, DaemonPathReceipt]:
        """Allocate repo/worktree/bundle directories for a conveyor item."""

        return self._allocate(
            repo=repo,
            branch_name=branch_name,
            pr_number=pr_number,
            base_sha=base_sha,
            head_sha=head_sha,
            path_kinds=("repo", "worktree", "bundle"),
            label=f"{repo}-{branch_name}",
        )

    def allocate_integrator_workspace(
        self,
        *,
        repo: str,
        pr_number: int,
        head_sha: str | None = None,
    ) -> tuple[DaemonPathAllocation, DaemonPathReceipt]:
        """Allocate one randomized workspace directory for an integrator repair."""

        return self._allocate(
            repo=repo,
            branch_name=None,
            pr_number=pr_number,
            base_sha=None,
            head_sha=head_sha,
            path_kinds=("workspace",),
            label=f"{repo}-pr-{pr_number}",
        )

    def verify_receipt(
        self,
        receipt: DaemonPathReceipt,
        allocation: DaemonPathAllocation | None = None,
    ) -> DaemonPathAllocation:
        """Return the issued allocation when ``receipt`` is valid and active."""

        issued = self._verify_receipt(receipt, allow_cleaned=False)
        if allocation is not None:
            self._assert_allocation_confined(allocation)
            if allocation != issued:
                raise DaemonReceiptError("receipt does not match supplied allocation")
        return issued

    def cleanup(self, receipt: DaemonPathReceipt) -> bool:
        """Remove allocation-owned paths; repeated cleanup is safe and silent."""

        allocation = self._verify_receipt(receipt, allow_cleaned=True)
        if allocation.allocation_id in self._cleaned:
            return False

        removed = False
        paths = sorted((path for _field, _kind, path in allocation.iter_paths()), key=lambda p: len(p.parts), reverse=True)
        for field_name, kind, path in allocation.iter_paths():
            confined = self._roots.confine_path(path, kind)
            if confined.exists():
                if confined.is_dir():
                    shutil.rmtree(confined)
                else:
                    confined.unlink()
                removed = True

        self._cleaned.add(allocation.allocation_id)
        return removed or bool(paths)

    def _allocate(
        self,
        *,
        repo: str,
        branch_name: str | None,
        pr_number: int | None,
        base_sha: str | None,
        head_sha: str | None,
        path_kinds: tuple[str, ...],
        label: str,
    ) -> tuple[DaemonPathAllocation, DaemonPathReceipt]:
        allocation_id = self._unique_token(self._allocation_id_factory, self._allocations)
        nonce = self._nonce_factory()
        created: list[Path] = []
        path_values: dict[str, Path] = {}
        provenance: list[tuple[str, str]] = []

        try:
            for kind in path_kinds:
                root = self._roots.root_for(kind)
                path = Path(tempfile.mkdtemp(prefix=f"{_safe_label(label)}-{allocation_id[:8]}-", dir=root))
                path.chmod(0o700)
                confined = self._roots.confine_path(path, kind)
                created.append(confined)
                field_name = f"{kind}_path"
                path_values[field_name] = confined
                provenance.append((field_name, kind))

            allocation = DaemonPathAllocation(
                allocation_id=allocation_id,
                nonce=nonce,
                created_at=self._clock(),
                repo=repo,
                branch_name=branch_name,
                pr_number=pr_number,
                base_sha=base_sha,
                head_sha=head_sha,
                root_provenance=tuple(provenance),
                **path_values,
            )
            self._assert_allocation_confined(allocation)
            signature = self._signature(allocation)
            receipt = DaemonPathReceipt(allocation_id=allocation_id, nonce=nonce, signature=signature)
            self._allocations[allocation_id] = allocation
            self._signatures[allocation_id] = signature
            return allocation, receipt
        except Exception:
            for path in reversed(created):
                if path.exists():
                    shutil.rmtree(path)
            raise

    def _unique_token(self, factory: Callable[[], str], existing: dict[str, object]) -> str:
        for _attempt in range(100):
            token = factory()
            if token and token not in existing:
                return token
        raise DaemonAllocationError("could not generate a unique allocation id")

    def _verify_receipt(self, receipt: DaemonPathReceipt, *, allow_cleaned: bool) -> DaemonPathAllocation:
        allocation = self._allocations.get(receipt.allocation_id)
        if allocation is None:
            raise DaemonReceiptError("receipt was not issued by this allocator")
        if not allow_cleaned and receipt.allocation_id in self._cleaned:
            raise DaemonReceiptError("allocation has been cleaned up")
        if not hmac.compare_digest(receipt.nonce, allocation.nonce):
            raise DaemonReceiptError("receipt nonce does not match allocation")
        expected = self._signatures.get(receipt.allocation_id, "")
        actual = self._signature(allocation)
        if not hmac.compare_digest(expected, actual) or not hmac.compare_digest(receipt.signature, actual):
            raise DaemonReceiptError("receipt signature does not match allocation")
        self._assert_allocation_confined(allocation)
        return allocation

    def _assert_allocation_confined(self, allocation: DaemonPathAllocation) -> None:
        seen = False
        for _field_name, kind, path in allocation.iter_paths():
            seen = True
            self._roots.confine_path(path, kind)
        if not seen:
            raise DaemonRootError("allocation contains no daemon-owned paths")

    def _signature(self, allocation: DaemonPathAllocation) -> str:
        payload = {
            "allocation_id": allocation.allocation_id,
            "nonce": allocation.nonce,
            "repo": allocation.repo,
            "branch_name": allocation.branch_name,
            "pr_number": allocation.pr_number,
            "base_sha": allocation.base_sha,
            "head_sha": allocation.head_sha,
            "paths": {
                field_name: str(path)
                for field_name, _kind, path in allocation.iter_paths()
            },
            "root_provenance": list(allocation.root_provenance),
        }
        message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(hmac.new(self._secret, message, hashlib.sha256).digest()).hexdigest()


__all__ = [
    "DaemonAllocationError",
    "DaemonPathAllocation",
    "DaemonPathAllocator",
    "DaemonPathReceipt",
    "DaemonReceiptError",
    "DaemonRootError",
    "DaemonRuntimeRoots",
]
