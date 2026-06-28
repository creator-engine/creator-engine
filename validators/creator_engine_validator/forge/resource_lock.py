"""Local forge resource locks backed by ``.ce/state`` records.

These locks coordinate shared local resources such as worktrees or branch
territories. They are intentionally self-contained: no forge network calls, no
CLI coupling, and no imports from broader forge automation modules.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

DEFAULT_STATE_ROOT: Final[Path] = Path(".ce/state")
LOCKS_DIR: Final[Path] = Path("resource-locks")
LOCK_VERSION: Final[int] = 1


class ResourceLockError(Exception):
    """Base error for resource-lock failures."""


class ResourceLockContended(ResourceLockError):
    """Raised when an active lock is held by another holder."""

    def __init__(self, resource_id: str, holder: str | None, *, record: "LockRecord | None" = None):
        self.resource_id = resource_id
        self.holder = holder
        self.record = record
        detail = f"resource {resource_id!r} is locked"
        if holder:
            detail = f"{detail} by {holder!r}"
        super().__init__(detail)


class ResourceLockOwnershipError(ResourceLockError):
    """Raised when a holder attempts to release another holder's lock."""


@dataclass(frozen=True)
class LockRecord:
    """A durable resource-lock record."""

    resource_id: str
    holder: str
    acquired_at: datetime
    expires_at: datetime
    ttl_seconds: float
    path: Path | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, path: Path | None = None) -> "LockRecord":
        if payload.get("version") != LOCK_VERSION:
            raise ResourceLockError("unsupported resource lock version")
        resource_id = payload.get("resource_id")
        holder = payload.get("holder")
        ttl_seconds = payload.get("ttl_seconds")
        if not isinstance(resource_id, str) or not resource_id:
            raise ResourceLockError("resource lock record has invalid resource_id")
        if not isinstance(holder, str) or not holder:
            raise ResourceLockError("resource lock record has invalid holder")
        if not isinstance(ttl_seconds, (int, float)) or ttl_seconds <= 0:
            raise ResourceLockError("resource lock record has invalid ttl_seconds")
        return cls(
            resource_id=resource_id,
            holder=holder,
            acquired_at=_parse_utc(payload.get("acquired_at"), "acquired_at"),
            expires_at=_parse_utc(payload.get("expires_at"), "expires_at"),
            ttl_seconds=float(ttl_seconds),
            path=path,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "version": LOCK_VERSION,
            "resource_id": self.resource_id,
            "holder": self.holder,
            "acquired_at": _format_utc(self.acquired_at),
            "expires_at": _format_utc(self.expires_at),
            "ttl_seconds": self.ttl_seconds,
        }

    def is_stale(self, now: datetime | None = None) -> bool:
        return _coerce_now(now) >= self.expires_at


def acquire(
    resource_id: str,
    holder: str,
    *,
    ttl: float | int | timedelta,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    now: datetime | None = None,
) -> LockRecord:
    """Acquire ``resource_id`` for ``holder`` or fail closed on contention."""

    clean_resource = _require_nonempty(resource_id, "resource_id")
    clean_holder = _require_nonempty(holder, "holder")
    ttl_seconds = _ttl_seconds(ttl)
    root = _locks_root(state_root)
    lock_path = _lock_path(root, clean_resource)
    reclaim_path = _reclaim_path(root, clean_resource)

    root.mkdir(parents=True, exist_ok=True)
    current_time = _coerce_now(now)
    record = LockRecord(
        resource_id=clean_resource,
        holder=clean_holder,
        acquired_at=current_time,
        expires_at=current_time + timedelta(seconds=ttl_seconds),
        ttl_seconds=ttl_seconds,
        path=lock_path,
    )

    try:
        _write_new_record(lock_path, record)
        return record
    except FileExistsError:
        pass

    existing = _read_record(lock_path)
    if not existing.is_stale(current_time):
        raise ResourceLockContended(clean_resource, existing.holder, record=existing)

    with _reclaim_guard(reclaim_path):
        try:
            latest = _read_record(lock_path)
        except FileNotFoundError:
            latest = None
        if latest is not None and not latest.is_stale(current_time):
            raise ResourceLockContended(clean_resource, latest.holder, record=latest)
        if latest is not None:
            lock_path.unlink()
        try:
            _write_new_record(lock_path, record)
        except FileExistsError as exc:
            winner = _read_record(lock_path)
            raise ResourceLockContended(clean_resource, winner.holder, record=winner) from exc
    return record


def release(
    resource_id: str,
    holder: str,
    *,
    state_root: str | Path = DEFAULT_STATE_ROOT,
) -> bool:
    """Release ``resource_id`` if held by ``holder``.

    Returns ``False`` when the resource has no lock record. A wrong-holder
    release raises ``ResourceLockOwnershipError`` and leaves the lock intact.
    """

    clean_resource = _require_nonempty(resource_id, "resource_id")
    clean_holder = _require_nonempty(holder, "holder")
    lock_path = _lock_path(_locks_root(state_root), clean_resource)
    try:
        record = _read_record(lock_path)
    except FileNotFoundError:
        return False
    if record.holder != clean_holder:
        raise ResourceLockOwnershipError(
            f"resource {clean_resource!r} is held by {record.holder!r}, not {clean_holder!r}"
        )
    lock_path.unlink()
    return True


def is_held(
    resource_id: str,
    *,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    now: datetime | None = None,
) -> bool:
    """Return whether ``resource_id`` has an active, non-stale lock."""

    clean_resource = _require_nonempty(resource_id, "resource_id")
    lock_path = _lock_path(_locks_root(state_root), clean_resource)
    try:
        record = _read_record(lock_path)
    except FileNotFoundError:
        return False
    return not record.is_stale(now)


def list_held(
    *,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    now: datetime | None = None,
) -> tuple[LockRecord, ...]:
    """Return active lock records sorted by resource id."""

    root = _locks_root(state_root)
    if not root.exists():
        return ()
    current_time = _coerce_now(now)
    records: list[LockRecord] = []
    for path in _record_paths(root):
        record = _read_record(path)
        if not record.is_stale(current_time):
            records.append(record)
    return tuple(sorted(records, key=lambda record: record.resource_id))


def _locks_root(state_root: str | Path) -> Path:
    return Path(state_root) / LOCKS_DIR


def _lock_path(root: Path, resource_id: str) -> Path:
    digest = hashlib.sha256(resource_id.encode("utf-8")).hexdigest()
    return root / f"{digest}.json"


def _reclaim_path(root: Path, resource_id: str) -> Path:
    digest = hashlib.sha256(resource_id.encode("utf-8")).hexdigest()
    return root / f".{digest}.reclaim"


def _record_paths(root: Path) -> Iterable[Path]:
    return (path for path in root.glob("*.json") if path.is_file())


def _write_new_record(path: Path, record: LockRecord) -> None:
    payload = json.dumps(record.to_payload(), sort_keys=True) + "\n"
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(payload)


def _read_record(path: Path) -> LockRecord:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise ResourceLockError(f"could not read resource lock record {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ResourceLockError("resource lock record must be a JSON object")
    return LockRecord.from_payload(payload, path=path)


class _reclaim_guard:
    def __init__(self, path: Path):
        self._path = path
        self._fd: int | None = None

    def __enter__(self) -> "_reclaim_guard":
        try:
            self._fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise ResourceLockContended(self._path.stem, None) from exc
        os.write(self._fd, str(time.time()).encode("ascii"))
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ResourceLockError(f"resource lock record has invalid {field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResourceLockError(f"resource lock record has invalid {field}") from exc
    if parsed.tzinfo is None:
        raise ResourceLockError(f"resource lock record {field} must include timezone")
    return parsed.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _coerce_now(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _ttl_seconds(ttl: float | int | timedelta) -> float:
    seconds = ttl.total_seconds() if isinstance(ttl, timedelta) else float(ttl)
    if seconds <= 0:
        raise ValueError("ttl must be positive")
    return seconds


def _require_nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()
