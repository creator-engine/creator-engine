"""Verified, seat-side handoff from intake ownership to a governed launcher.

The adapter is deliberately a consumer of controller evidence, not a new claim
authority.  It validates a controller-exported snapshot of the normal
``work_claims`` marker state and territory check, then fences the queue claim
before invoking the already-governed launch seam.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from creator_engine_validator import work_claims
from creator_engine_validator.conveyor_intake_queue import IntakeQueue, IntakeTransitionError, IntakeUnit
from creator_engine_validator.work_sizing import WORK_CLASSES


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BRANCH = re.compile(r"^(?!/)(?!.*//)(?!.*\.\.)(?!.*@\{)[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MAX_TERRITORY_PATHS = 64
_MAX_TERRITORY_PATH = 512
PullState = Literal["empty", "launched", "blocked_released", "blocked_retained"]
ClaimState = Literal["empty", "claimed", "launching"]


@dataclass(frozen=True)
class VerifiedLaneLaunch:
    """Metadata for the governed seam, with an adapter-owned brief snapshot."""

    unit_id: str
    brief_snapshot: "VerifiedBriefSnapshot"
    brief_sha256: str
    branch: str
    worktree: str
    work_class: str
    territory_paths: tuple[str, ...]
    territory_digest: str
    claim_generation: int


@dataclass
class VerifiedBriefSnapshot:
    """A no-follow, descriptor-anchored snapshot for one launcher invocation."""

    directory_fd: int
    filename: str
    device: int
    inode: int
    digest: str
    _closed: bool = False

    def read_bytes(self) -> bytes:
        """Read the exact snapshot identity, refusing a replacement before use."""
        if self._closed:
            raise ValueError("verified snapshot is no longer available")
        fd = os.open(
            self.filename,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=self.directory_fd,
        )
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or (info.st_dev, info.st_ino) != (self.device, self.inode)
            ):
                raise ValueError("verified snapshot was replaced before launcher consumption")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            content = b"".join(chunks)
            if hashlib.sha256(content).hexdigest() != self.digest:
                raise ValueError("verified snapshot content no longer matches its digest")
            return content
        finally:
            os.close(fd)

    def close(self) -> None:
        if not self._closed:
            os.close(self.directory_fd)
            self._closed = True


@dataclass(frozen=True)
class SeatPullOutcome:
    state: PullState
    claim_state: ClaimState
    seat_id: str
    unit_id: str | None = None
    brief_sha256: str | None = None
    detail: str | None = None


GovernedLaneLauncher = Callable[[VerifiedLaneLaunch], bool]


class SeatPullAdapter:
    """Claim, verify controller evidence, fence, and hand one unit to a launcher.

    ``controller_evidence_root`` is a trusted controller-owned state root.  Its
    ``<unit_id>.json`` records are evidence only: they contain a snapshot of a
    *normal* ``work_claims`` comment set and the controller's territory result;
    they never mint or replace a work claim.
    """

    def __init__(
        self,
        queue: IntakeQueue,
        *,
        trusted_brief_root: Path,
        trusted_worktree_root: Path,
        controller_evidence_root: Path | None = None,
        governed_lane_launcher: GovernedLaneLauncher,
    ) -> None:
        self.queue = queue
        self.trusted_brief_root = Path(trusted_brief_root)
        self.trusted_worktree_root = Path(trusted_worktree_root)
        self.controller_evidence_root = Path(controller_evidence_root or queue.root / "controller-evidence")
        self.governed_lane_launcher = governed_lane_launcher

    def pull_one(self, seat_id: str, *, ttl_seconds: float | int = 300, clock: Callable[[], str] | None = None) -> SeatPullOutcome:
        """Perform one bounded pull.  A failed launch is released for retry.

        Once preflight passes, ``fence_launch`` makes the record non-reclaimable
        while the launcher runs.  An exception after that point is retained:
        launch outcome is unknown, so retrying could duplicate a seat.
        """
        _validate_identity(seat_id, "seat_id")
        unit = self.queue.claim_entry(seat_id, ttl_seconds=ttl_seconds, clock=clock)
        if unit is None:
            return SeatPullOutcome(state="empty", claim_state="empty", seat_id=seat_id)
        try:
            launch = self._verified_launch(unit, seat_id)
        except (OSError, ValueError, PermissionError) as exc:
            return self._release(unit, seat_id, f"verification_refused:{type(exc).__name__}", clock)
        try:
            fenced = self.queue.fence_launch(unit.unit_id, seat_id, _claim_token(unit), clock=clock)
            launch = _with_generation(launch, fenced.claim_generation)
        except (OSError, ValueError, PermissionError, IntakeTransitionError) as exc:
            try:
                launch.brief_snapshot.close()
            finally:
                return self._release(unit, seat_id, f"launch_fence_refused:{type(exc).__name__}", clock)
        try:
            accepted = self.governed_lane_launcher(launch)
        except Exception as exc:
            return SeatPullOutcome(
                state="blocked_retained", claim_state="launching", seat_id=seat_id,
                unit_id=unit.unit_id, brief_sha256=unit.brief_sha,
                detail=f"launcher_outcome_unknown:{type(exc).__name__}",
            )
        finally:
            launch.brief_snapshot.close()
        if not accepted:
            return self._release(fenced, seat_id, "launcher_refused", clock)
        return SeatPullOutcome(
            state="launched", claim_state="launching", seat_id=seat_id,
            unit_id=unit.unit_id, brief_sha256=unit.brief_sha,
        )

    def _verified_launch(self, unit: IntakeUnit, seat_id: str) -> VerifiedLaneLaunch:
        _validate_metadata(unit, self.trusted_worktree_root)
        if not _SHA256.fullmatch(unit.brief_sha):
            raise ValueError("brief_sha must be a lowercase 64-hex SHA-256 for seat pull")
        brief_bytes = _read_trusted_brief(self.trusted_brief_root, unit.brief_ref)
        actual_sha = hashlib.sha256(brief_bytes).hexdigest()
        if actual_sha != unit.brief_sha:
            raise ValueError("brief_sha does not match trusted brief content")
        territory_paths = _canonical_territory_paths(unit.territory_paths)
        territory_digest = _territory_digest(territory_paths)
        _validate_controller_evidence(
            self.controller_evidence_root, unit, seat_id, actual_sha, territory_paths, territory_digest
        )
        snapshot = _write_snapshot(self.trusted_brief_root, actual_sha, brief_bytes)
        return VerifiedLaneLaunch(
            unit_id=unit.unit_id, brief_snapshot=snapshot, brief_sha256=actual_sha,
            branch=unit.branch, worktree=unit.worktree, work_class=unit.work_class,
            territory_paths=territory_paths, territory_digest=territory_digest,
            claim_generation=unit.claim_generation,
        )

    def _release(self, unit: IntakeUnit, seat_id: str, detail: str, clock: Callable[[], str] | None) -> SeatPullOutcome:
        try:
            self.queue.release_entry(unit.unit_id, seat_id, claim_token=_claim_token(unit), clock=clock)
        except Exception as exc:
            return SeatPullOutcome(
                state="blocked_retained", claim_state="launching" if unit.status == "launching" else "claimed",
                seat_id=seat_id, unit_id=unit.unit_id, brief_sha256=unit.brief_sha,
                detail=f"{detail};release_failed:{type(exc).__name__}",
            )
        return SeatPullOutcome(
            state="blocked_released", claim_state="claimed", seat_id=seat_id,
            unit_id=unit.unit_id, brief_sha256=unit.brief_sha, detail=detail,
        )


def _validate_metadata(unit: IntakeUnit, trusted_worktree_root: Path) -> None:
    _validate_identity(unit.unit_id, "unit_id")
    if (
        not _BRANCH.fullmatch(unit.branch)
        or unit.branch.endswith((".", ".lock", "/"))
        or any(part.startswith(".") or part.endswith(".lock") for part in unit.branch.split("/"))
    ):
        raise ValueError("branch is not a canonical branch name")
    if unit.work_class not in WORK_CLASSES:
        raise ValueError("work_class is not canonical")
    worktree = Path(unit.worktree)
    if not worktree.is_absolute() or ".." in worktree.parts:
        raise ValueError("worktree must be an absolute canonical owned path")
    if trusted_worktree_root.is_symlink():
        raise ValueError("owned worktree root must not be a symlink")
    root = trusted_worktree_root.resolve(strict=True)
    try:
        worktree.relative_to(root)
    except ValueError as exc:
        raise ValueError("worktree is outside the owned worktree root") from exc
    candidate = root
    for component in worktree.relative_to(root).parts:
        candidate /= component
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            break
        if stat.S_ISLNK(info.st_mode):
            raise ValueError("worktree path must not contain a symlink")
    try:
        resolved_worktree = worktree.resolve(strict=False)
        resolved_worktree.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("worktree resolves outside the owned worktree root") from exc
    _canonical_territory_paths(unit.territory_paths)


def _canonical_territory_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    if not paths or len(paths) > _MAX_TERRITORY_PATHS:
        raise ValueError("territory_paths must be a bounded non-empty sequence")
    normalized: list[str] = []
    for path in paths:
        if not isinstance(path, str) or not path or len(path) > _MAX_TERRITORY_PATH:
            raise ValueError("territory path must be a bounded non-empty string")
        candidate = path.rstrip("/")
        pure = Path(candidate)
        if (
            not candidate or pure.is_absolute() or ".." in pure.parts or "." in pure.parts
            or "" in pure.parts or "//" in path or "\\" in path
        ):
            raise ValueError("territory path must be normalized and relative")
        if candidate != path and not path.endswith("/"):
            raise ValueError("territory path must be normalized")
        normalized.append(candidate)
    if len(set(normalized)) != len(normalized):
        raise ValueError("territory paths must not contain duplicates")
    return tuple(sorted(normalized))


def _territory_digest(paths: tuple[str, ...]) -> str:
    return hashlib.sha256(("\n".join(paths) + "\n").encode("utf-8")).hexdigest()


def _validate_controller_evidence(
    root: Path, unit: IntakeUnit, seat_id: str, brief_sha: str,
    territory_paths: tuple[str, ...], territory_digest: str,
) -> None:
    path = root / f"{unit.unit_id}.json"
    data = _read_json_regular(path)
    if not isinstance(data, Mapping):
        raise ValueError("controller evidence must be a JSON object")
    for field, expected in (("unit_id", unit.unit_id), ("brief_sha256", brief_sha), ("seat_id", seat_id), ("territory_digest", territory_digest)):
        if data.get(field) != expected:
            raise PermissionError(f"controller evidence {field} does not bind this pull")
    controller_id = data.get("controller_id")
    if not isinstance(controller_id, str):
        raise ValueError("controller evidence lacks controller_id")
    _validate_identity(controller_id, "controller_id")
    if data.get("state") != "active" or data.get("collision_free") is not True:
        raise PermissionError("controller evidence is released or colliding")
    evidence_paths = data.get("territory_paths")
    if not isinstance(evidence_paths, list) or tuple(evidence_paths) != territory_paths:
        raise PermissionError("controller territory evidence does not match canonical paths")
    claim = data.get("work_claim")
    if not isinstance(claim, Mapping):
        raise ValueError("controller evidence lacks normal work_claim snapshot")
    work_key = claim.get("work_key")
    comments = claim.get("comments")
    if not isinstance(work_key, str) or not isinstance(comments, list):
        raise ValueError("work_claim snapshot is malformed")
    key = work_claims.parse_ticket(work_key)
    parsed_comments: list[work_claims.Comment] = []
    for raw in comments:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), int) or not isinstance(raw.get("body"), str):
            raise ValueError("work_claim comment snapshot is malformed")
        parsed_comments.append(work_claims.Comment(raw["id"], raw["body"], str(raw.get("created_at", ""))))
    state = work_claims.compute_state(parsed_comments, key.work_key, datetime.now(timezone.utc))
    active = state.active
    if active is None or active.status != "active" or active.stale or active.holder != controller_id:
        raise PermissionError("normal controller work claim is absent, released, stale, or foreign")
    if state.invalid_count or any(entry.status == "conflict" for entry in state.entries):
        raise PermissionError("normal controller work claim is colliding")


def _read_trusted_brief(root: Path, brief_ref: str) -> bytes:
    parts = _safe_relative_parts(brief_ref, "brief_ref")
    if root.is_symlink():
        raise ValueError("trusted brief root must not be a symlink")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    fd = root_fd
    try:
        for index, part in enumerate(parts):
            component = os.stat(part, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISLNK(component.st_mode):
                raise ValueError("brief_ref contains a symlink")
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            if index < len(parts) - 1:
                flags |= os.O_DIRECTORY
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("brief_ref is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(fd)


def _safe_relative_parts(value: str, field: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"{field} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{field} escapes trusted root")
    return tuple(path.parts)


def _write_snapshot(root: Path, digest: str, content: bytes) -> VerifiedBriefSnapshot:
    root_fd = _open_directory_nofollow(root, "trusted brief root")
    try:
        try:
            os.mkdir(".verified-snapshots", mode=0o700, dir_fd=root_fd)
        except FileExistsError:
            pass
        snapshots_fd = _open_child_directory_nofollow(root_fd, ".verified-snapshots", "verified snapshot root")
        try:
            with _snapshot_publish_guard(snapshots_fd, digest):
                return _publish_snapshot(snapshots_fd, digest, content)
        except BaseException:
            os.close(snapshots_fd)
            raise
    finally:
        os.close(root_fd)


def _open_directory_nofollow(path: Path, label: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            raise ValueError(f"{label} is unsafe")
        return fd
    except BaseException:
        os.close(fd)
        raise


class _snapshot_publish_guard:
    """Serialize publishers of one digest while repairing old crash residue."""

    def __init__(self, snapshots_fd: int, digest: str) -> None:
        self._snapshots_fd = snapshots_fd
        self._name = f".{digest}.snapshot.lock"
        self._fd: int | None = None

    def __enter__(self) -> "_snapshot_publish_guard":
        self._fd = os.open(self._name, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=self._snapshots_fd)
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


def _publish_snapshot(snapshots_fd: int, digest: str, content: bytes) -> VerifiedBriefSnapshot:
    filename = f"{digest}.brief"
    _recover_snapshot_temps(snapshots_fd, digest)
    tmp_name = f".{digest}.snapshot-{secrets.token_hex(16)}.tmp"
    fd = os.open(
        tmp_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
        dir_fd=snapshots_fd,
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        # A hard link creates the final name atomically without ever replacing
        # a concurrently verified publisher's file.
        while True:
            try:
                os.link(
                    tmp_name, filename, src_dir_fd=snapshots_fd,
                    dst_dir_fd=snapshots_fd, follow_symlinks=False,
                )
            except FileExistsError:
                if _snapshot_matches_digest(snapshots_fd, filename, digest):
                    break
                _remove_corrupt_snapshot(snapshots_fd, filename, digest)
                continue
            else:
                os.fsync(snapshots_fd)
                break
        os.unlink(tmp_name, dir_fd=snapshots_fd)
        os.fsync(snapshots_fd)
    except BaseException:
        try:
            os.unlink(tmp_name, dir_fd=snapshots_fd)
            os.fsync(snapshots_fd)
        except OSError:
            pass
        raise
    return _verified_snapshot_handle(snapshots_fd, filename, digest)


def _open_child_directory_nofollow(parent_fd: int, name: str, label: str) -> int:
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"{label} is unsafe")
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(name, flags, dir_fd=parent_fd)
    try:
        opened = os.fstat(fd)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
        ):
            raise ValueError(f"{label} is unsafe")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_json_regular(path: Path) -> object:
    return json.loads(_read_regular_bytes(path, "evidence").decode("utf-8"))


def _read_regular_bytes(path: Path, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_regular_bytes_at(parent_fd: int, name: str, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(name, flags, dir_fd=parent_fd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _verified_snapshot_handle(snapshots_fd: int, filename: str, digest: str) -> VerifiedBriefSnapshot:
    """Transfer a verified snapshot directory descriptor to the launch seam."""
    fd = os.open(filename, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=snapshots_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("verified snapshot is not a regular file")
        content = _read_fd_bytes(fd)
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("content-addressed snapshot digest collision")
        return VerifiedBriefSnapshot(snapshots_fd, filename, info.st_dev, info.st_ino, digest)
    finally:
        os.close(fd)


def _recover_snapshot_temps(snapshots_fd: int, digest: str) -> None:
    """Remove only our private, unlinked-publish residues after a crash."""
    prefix = f".{digest}.snapshot-"
    removed = False
    for name in os.listdir(snapshots_fd):
        if not name.startswith(prefix) or not name.endswith(".tmp"):
            continue
        info = os.stat(name, dir_fd=snapshots_fd, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("verified snapshot crash residue is unsafe")
        os.unlink(name, dir_fd=snapshots_fd)
        removed = True
    if removed:
        os.fsync(snapshots_fd)


def _snapshot_matches_digest(snapshots_fd: int, filename: str, digest: str) -> bool:
    return hashlib.sha256(_read_regular_bytes_at(snapshots_fd, filename, "verified snapshot")).hexdigest() == digest


def _remove_corrupt_snapshot(snapshots_fd: int, filename: str, digest: str) -> bool:
    """Discard a pre-atomic partial final only when identity stays stable."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(filename, flags, dir_fd=snapshots_fd)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError("verified snapshot crash residue is unsafe")
        if hashlib.sha256(_read_fd_bytes(fd)).hexdigest() == digest:
            return False
        current = os.stat(filename, dir_fd=snapshots_fd, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            return False
        os.unlink(filename, dir_fd=snapshots_fd)
        os.fsync(snapshots_fd)
        return True
    finally:
        os.close(fd)


def _read_fd_bytes(fd: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _validate_identity(value: str, field: str) -> None:
    if not isinstance(value, str) or not _IDENTITY.fullmatch(value):
        raise ValueError(f"{field} is not a canonical identity")


def _claim_token(unit: IntakeUnit) -> str:
    if unit.claim_token is None:
        raise PermissionError("claimed unit lacks an ownership token")
    return unit.claim_token


def _with_generation(launch: VerifiedLaneLaunch, generation: int) -> VerifiedLaneLaunch:
    return VerifiedLaneLaunch(
        unit_id=launch.unit_id, brief_snapshot=launch.brief_snapshot, brief_sha256=launch.brief_sha256,
        branch=launch.branch, worktree=launch.worktree, work_class=launch.work_class,
        territory_paths=launch.territory_paths, territory_digest=launch.territory_digest,
        claim_generation=generation,
    )
