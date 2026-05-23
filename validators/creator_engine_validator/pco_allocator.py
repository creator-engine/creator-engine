"""PCO Slice 2R: Worktree Allocator Runtime.

Implements pco-allocate (PCO-027), pco-release (PCO-028),
claim-writes-only-under-held-lease enforcement (PCO-029), and the
callable pane-launch guard (PCO-030).

Root-checkout refusal (PCO-031) is enforced by detecting whether the
provided repo_root has ``.git`` as a real directory (main checkout) vs
a plain file (``git worktree add`` secondary worktree).

This module performs NO GitHub/tracker mutation, NO branch deletion,
NO push, NO autonomous action outside the physical lease/claim/event
record writes under the lane's advisory lock.

Prose contract: ``docs/operations/WORKTREE_ALLOCATOR_PROTOCOL.md``.
"""
from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator

import yaml

from .checks.active_work_ledger_conflicts import validate_active_work_ledger_conflicts
from .checks.active_work_ledger_schema import validate_active_work_ledger_record
from .checks.worktree_lease_schema import validate_worktree_lease_record
from .reporting import CheckResult

CONTROLLER_ID_ENV = "CREATOR_ENGINE_CONTROLLER_ID"
_CONTROLLER_ID_FILE_REL = ".hermes/controller-id"


class PcoAllocatorError(Exception):
    """Base class for allocator runtime errors."""


class RootCheckoutRefused(PcoAllocatorError):
    """pco-allocate / pco-release refused because repo_root is the main checkout."""


class ControllerIdentityError(PcoAllocatorError):
    """Controller identity could not be resolved."""


class PcoConflictError(PcoAllocatorError):
    """Preflight conflict check refused the allocation."""


class AllocationError(PcoAllocatorError):
    """git worktree add or record write failed; lease rolled back."""


# ---------------------------------------------------------------------------
# PCO-031: root-checkout detection
# ---------------------------------------------------------------------------


def is_root_checkout(repo_path: Path) -> bool:
    """Return True when ``repo_path`` is the main (root) git checkout.

    In a ``git worktree add`` secondary worktree, ``.git`` is a plain
    file containing the ``gitdir:`` pointer.  In the main checkout it
    is a real directory.  Symlinks to a directory are treated as
    non-root to avoid false positives on exotic setups.
    """
    dot_git = repo_path / ".git"
    return dot_git.is_dir() and not dot_git.is_symlink()


# ---------------------------------------------------------------------------
# Controller identity resolution
# ---------------------------------------------------------------------------


def resolve_controller_id(repo_path: Path) -> str | None:
    """Resolve the local controller_id from existing conventions.

    Resolution order:
    1. ``CREATOR_ENGINE_CONTROLLER_ID`` env var.
    2. ``.hermes/controller-id`` file under ``repo_path``.
    3. The most-recently-touched claims directory under
       ``.hermes/active-work-ledger/claims/``.

    Returns ``None`` when no convention yields a value.
    """
    env_val = os.environ.get(CONTROLLER_ID_ENV, "").strip()
    if env_val:
        return env_val

    id_file = repo_path / _CONTROLLER_ID_FILE_REL
    if id_file.is_file():
        text = id_file.read_text(encoding="utf-8").strip()
        if text:
            return text

    claims_dir = repo_path / ".hermes" / "active-work-ledger" / "claims"
    if claims_dir.is_dir():
        controller_dirs = [d for d in claims_dir.iterdir() if d.is_dir()]
        if controller_dirs:
            controller_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            return controller_dirs[0].name

    return None


# ---------------------------------------------------------------------------
# Advisory lane lock
# ---------------------------------------------------------------------------


@contextmanager
def _lane_lock(lock_dir: Path, lane_id: str) -> Iterator[None]:
    """Exclusive advisory ``flock`` on ``<lock_dir>/<lane_id>.lock``."""
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{lane_id}.lock"
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# PCO-030: callable pane-launch guard
# ---------------------------------------------------------------------------


def guard(ledger_root: Path, *, now: datetime | None = None) -> CheckResult:
    """Callable runtime guard for pane-launch gating (PCO-030).

    Wraps ``validate_active_work_ledger_conflicts`` as a pure read-only
    callable.  Returns a ``CheckResult``; callers MUST refuse pane launch
    when ``result.ok`` is ``False``.  This function has NO filesystem
    side effects and does NOT spawn panes or subprocesses.
    """
    return validate_active_work_ledger_conflicts([ledger_root], now=now)


# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` using a temp-then-rename atomic sequence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    nonce = uuid.uuid4().hex[:8]
    tmp = path.parent / f"{path.name}.tmp.{pid}.{nonce}"
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


# ---------------------------------------------------------------------------
# git helpers (replaceable via _git_fn test seam)
# ---------------------------------------------------------------------------


def _git_worktree_add(repo_root: Path, worktree_path: Path, branch: str) -> None:
    """Run ``git worktree add -b <branch> <path>`` from ``repo_root``."""
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path)],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
    )


def _git_worktree_remove(repo_root: Path, worktree_path: Path) -> None:
    """Run ``git worktree remove <path>`` from ``repo_root``."""
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_path)],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------


def _utc_now_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expires_at_str(lease_seconds: int) -> str:
    dt = datetime.now(UTC) + timedelta(seconds=lease_seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_worktree_path(value: str) -> str:
    text = str(value or "").strip()
    while len(text) > 1 and text.endswith("/"):
        text = text[:-1]
    return text


def _check_proposed_worktree_conflict(ledger_root: Path, worktree_path: Path) -> None:
    """Raise PcoConflictError if any existing live claim targets the same worktree_path."""
    proposed_norm = _normalize_worktree_path(str(worktree_path))
    if not proposed_norm:
        return
    claims_dir = ledger_root / "claims"
    if not claims_dir.is_dir():
        return
    for controller_dir in claims_dir.iterdir():
        if not controller_dir.is_dir():
            continue
        for claim_file in controller_dir.glob("*.yaml"):
            if ".tmp." in claim_file.name:
                continue
            try:
                raw = claim_file.read_text(encoding="utf-8")
                existing = yaml.safe_load(raw)
            except Exception:
                continue
            if not isinstance(existing, dict):
                continue
            if existing.get("released_at"):
                continue
            existing_wt = _normalize_worktree_path(str(existing.get("worktree_path") or ""))
            if existing_wt and existing_wt == proposed_norm:
                raise PcoConflictError(
                    f"proposed worktree_path {str(worktree_path)!r} conflicts with "
                    f"existing live claim at {claim_file}"
                )


def _format_validation_errors(errors: list[Any]) -> str:
    return "; ".join(error.format() for error in errors)


def _validate_proposed_allocation_state(
    *,
    ledger_root: Path,
    lease_path: Path,
    lease_record: dict[str, Any],
    claim_path: Path,
    claim_record: dict[str, Any],
    event_path: Path,
    event_record: dict[str, Any],
) -> None:
    """Validate the full post-allocation ledger state before mutating the real ledger."""
    record_errors = [
        *validate_worktree_lease_record(lease_record, lease_path),
        *validate_active_work_ledger_record(claim_record, claim_path),
        *validate_active_work_ledger_record(event_record, event_path),
    ]
    if record_errors:
        raise PcoConflictError(
            "proposed allocation records fail schema validation: "
            f"{_format_validation_errors(record_errors)}"
        )

    with tempfile.TemporaryDirectory(prefix="pco-proposed-ledger-") as tmp:
        staged = Path(tmp) / "active-work-ledger"
        if ledger_root.exists():
            shutil.copytree(ledger_root, staged, dirs_exist_ok=True)
        else:
            staged.mkdir(parents=True)

        staged_lease = staged / lease_path.relative_to(ledger_root)
        staged_claim = staged / claim_path.relative_to(ledger_root)
        staged_event = staged / event_path.relative_to(ledger_root)
        for path, record in [
            (staged_lease, lease_record),
            (staged_claim, claim_record),
            (staged_event, event_record),
        ]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")

        proposed = guard(staged)
        if not proposed.ok:
            codes = ", ".join(error.code for error in proposed.errors)
            raise PcoConflictError(
                "active_work_ledger_conflicts refuses proposed allocation state: "
                f"{codes}"
            )


# ---------------------------------------------------------------------------
# PCO-027: pco-allocate
# ---------------------------------------------------------------------------


def allocate(
    *,
    repo_root: Path,
    ledger_root: Path,
    lane_id: str,
    worktree_path: Path,
    envelope_ref: str,
    branch: str,
    controller_id: str,
    lease_seconds: int = 3600,
    pane_label: str | None = None,
    _git_fn: Callable[..., None] | None = None,
) -> None:
    """PCO-027: allocate a worktree lane under an advisory lock.

    Sequence (all steps under the lane lock):
    1. Refuse if ``repo_root`` is the root checkout (PCO-031).
    2. Acquire exclusive advisory lock on ``<ledger_root>/locks/<lane_id>.lock``.
    3. Preflight: run ``active_work_ledger_conflicts`` guard; refuse on conflict.
    4. Write lease record atomically (PCO-029: lease precedes claim).
    5. Run ``git worktree add``; rollback lease on failure.
    6. Write claim record atomically.
    7. Write ``claim_created`` event record atomically.
    8. On any step-6/7 failure, rollback all records and remove worktree.

    Does NOT push, does NOT create GitHub issues/PRs, does NOT mutate
    branch configuration beyond the new worktree branch.
    """
    if is_root_checkout(repo_root):
        raise RootCheckoutRefused(
            "pco-allocate MUST NOT run from the root checkout; "
            "use an isolated per-gate worktree"
        )

    lock_dir = ledger_root / "locks"
    with _lane_lock(lock_dir, lane_id):
        # Step 3: preflight conflict check against existing ledger
        conflicts = guard(ledger_root)
        if not conflicts.ok:
            codes = ", ".join(e.code for e in conflicts.errors)
            raise PcoConflictError(
                f"active_work_ledger_conflicts refuses allocation: {codes}"
            )

        now = _utc_now_str()
        expires_at = _expires_at_str(lease_seconds)
        ts_compact = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        lease_id = f"lease-{lane_id}-{ts_compact}"
        event_id = f"claim-created-{ts_compact}"

        lease_path = ledger_root / "leases" / controller_id / f"{lane_id}.yaml"
        claim_path = ledger_root / "claims" / controller_id / f"{lane_id}.yaml"

        # Proposed-state validation — refuse before any mutation
        # Check 1: active claim already exists for this controller/lane
        if claim_path.is_file():
            try:
                raw = claim_path.read_text(encoding="utf-8")
                existing_claim = yaml.safe_load(raw)
                if isinstance(existing_claim, dict) and not existing_claim.get("released_at"):
                    raise PcoConflictError(
                        f"active claim already exists for {controller_id!r}/{lane_id!r}; "
                        "release the existing allocation before reallocating"
                    )
            except PcoConflictError:
                raise
            except Exception:
                pass

        # Check 2: proposed worktree_path conflicts with any existing live claim
        _check_proposed_worktree_conflict(ledger_root, worktree_path)
        event_dir = ledger_root / "events" / datetime.now(UTC).strftime("%Y/%m/%d")
        event_path = event_dir / f"{event_id}.yaml"

        lease_record: dict[str, Any] = {
            "kind": "worktree-lease-record",
            "record_type": "worktree_lease",
            "schema_version": "1",
            "controller_id": controller_id,
            "lane_id": lane_id,
            "record_timestamp": now,
            "lease_id": lease_id,
            "worktree_path": str(worktree_path),
            "acquired_at": now,
            "lease_seconds": lease_seconds,
            "expires_at": expires_at,
        }
        if pane_label:
            lease_record["pane_label"] = pane_label
        if branch:
            lease_record["branch"] = branch
        if envelope_ref:
            lease_record["envelope_ref"] = envelope_ref

        claim_record: dict[str, Any] = {
            "kind": "active-work-ledger-record",
            "record_type": "claim",
            "schema_version": "1",
            "controller_id": controller_id,
            "lane_id": lane_id,
            "record_timestamp": now,
            "worktree_path": str(worktree_path),
            "envelope_ref": envelope_ref,
            "lease_seconds": lease_seconds,
            "claimed_at": now,
            "last_heartbeat_at": now,
        }
        if pane_label:
            claim_record["pane_label"] = pane_label
        if branch:
            claim_record["branch"] = branch

        event_record: dict[str, Any] = {
            "kind": "active-work-ledger-record",
            "record_type": "event",
            "schema_version": "1",
            "controller_id": controller_id,
            "lane_id": lane_id,
            "record_timestamp": now,
            "event_kind": "claim_created",
            "event_id": event_id,
            "event_timestamp": now,
        }

        _validate_proposed_allocation_state(
            ledger_root=ledger_root,
            lease_path=lease_path,
            lease_record=lease_record,
            claim_path=claim_path,
            claim_record=claim_record,
            event_path=event_path,
            event_record=event_record,
        )

        # Step 4: write lease FIRST (PCO-029)
        _atomic_write(lease_path, yaml.safe_dump(lease_record, sort_keys=True))

        # Step 5: git worktree add
        try:
            git_add = _git_fn if _git_fn is not None else _git_worktree_add
            git_add(repo_root, worktree_path, branch)
        except Exception as exc:
            lease_path.unlink(missing_ok=True)
            raise AllocationError(
                f"git worktree add failed; lease rolled back: {exc}"
            ) from exc

        # Steps 6-7: write claim and event; rollback all on failure
        try:
            _atomic_write(claim_path, yaml.safe_dump(claim_record, sort_keys=True))
            _atomic_write(event_path, yaml.safe_dump(event_record, sort_keys=True))

        except Exception as exc:
            for p in [claim_path, event_path, lease_path]:
                p.unlink(missing_ok=True)
            try:
                git_rm = _git_fn if _git_fn is not None else _git_worktree_remove
                git_rm(repo_root, worktree_path)
            except Exception:
                pass
            raise AllocationError(
                f"record write failed after git add; rolled back: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# PCO-028: pco-release
# ---------------------------------------------------------------------------


def release(
    *,
    repo_root: Path,
    ledger_root: Path,
    lane_id: str,
    controller_id: str,
    release_reason: str = "completed",
    _git_fn: Callable[..., None] | None = None,
) -> None:
    """PCO-028: release a worktree lane under an advisory lock.

    Sequence (all steps under the lane lock, each tolerating prior-step
    completion for mid-sequence recovery):
    1. Refuse if ``repo_root`` is the root checkout (PCO-031).
    2. Acquire exclusive advisory lock.
    3. Mark claim released (``released_at`` + ``release_reason``).
       Tolerate missing claim file.
    4. Remove lease file. Tolerate already-absent lease.
    5. Append ``claim_released`` event.
    6. Run ``git worktree remove``. Tolerate already-removed worktree.

    Does NOT delete the branch. Does NOT push. Does NOT mutate GitHub.
    """
    if is_root_checkout(repo_root):
        raise RootCheckoutRefused(
            "pco-release MUST NOT run from the root checkout"
        )

    lock_dir = ledger_root / "locks"
    with _lane_lock(lock_dir, lane_id):
        now = _utc_now_str()
        claim_path = ledger_root / "claims" / controller_id / f"{lane_id}.yaml"
        lease_path = ledger_root / "leases" / controller_id / f"{lane_id}.yaml"
        event_dir = ledger_root / "events" / datetime.now(UTC).strftime("%Y/%m/%d")
        ts_compact = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        event_id = f"claim-released-{ts_compact}"
        event_path = event_dir / f"{event_id}.yaml"

        # Step 3: mark claim released (tolerate missing file; raise on read/write failure)
        worktree_path_str: str = ""
        if claim_path.is_file():
            try:
                raw = claim_path.read_text(encoding="utf-8")
                claim_record = yaml.safe_load(raw)
            except Exception as exc:
                raise PcoAllocatorError(
                    f"failed to load existing claim for release: {exc}"
                ) from exc

            if not isinstance(claim_record, dict):
                raise PcoAllocatorError("existing claim for release is not a YAML mapping")
            claim_errors = validate_active_work_ledger_record(claim_record, claim_path)
            if claim_errors:
                raise PcoAllocatorError(
                    "existing claim for release fails schema validation: "
                    f"{_format_validation_errors(claim_errors)}"
                )

            worktree_path_str = str(claim_record.get("worktree_path") or "")
            if not claim_record.get("released_at"):
                claim_record["released_at"] = now
                claim_record["release_reason"] = release_reason
            try:
                _atomic_write(
                    claim_path,
                    yaml.safe_dump(claim_record, sort_keys=True),
                )
            except Exception as exc:
                raise PcoAllocatorError(
                    f"failed to write claim release marker: {exc}"
                ) from exc

        # Step 4: remove lease (tolerate already absent; raise on removal failure)
        if lease_path.is_file():
            try:
                lease_path.unlink()
            except OSError as exc:
                raise PcoAllocatorError(f"failed to remove lease: {exc}") from exc

        # Step 5: append claim_released event
        event_record: dict[str, Any] = {
            "kind": "active-work-ledger-record",
            "record_type": "event",
            "schema_version": "1",
            "controller_id": controller_id,
            "lane_id": lane_id,
            "record_timestamp": now,
            "event_kind": "claim_released",
            "event_id": event_id,
            "event_timestamp": now,
        }
        try:
            _atomic_write(event_path, yaml.safe_dump(event_record, sort_keys=True))
        except Exception as exc:
            raise PcoAllocatorError(
                f"failed to write claim_released event: {exc}"
            ) from exc

        # Step 6: git worktree remove (tolerate already-removed; raise on failure)
        if worktree_path_str:
            wt = Path(worktree_path_str)
            if wt.exists():
                git_rm = _git_fn if _git_fn is not None else _git_worktree_remove
                try:
                    git_rm(repo_root, wt)
                except Exception as exc:
                    raise PcoAllocatorError(
                        f"git worktree remove failed for {worktree_path_str!r}: {exc}"
                    ) from exc
