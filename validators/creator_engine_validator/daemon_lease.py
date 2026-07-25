"""Fail-closed filesystem leases for armed governance daemons."""

from __future__ import annotations

import dataclasses
import errno
import json
import math
import os
import socket
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


DEFAULT_LEASE_TTL_SECONDS = 300.0
DEFAULT_LEASE_ROOT = Path(".ce/state/daemon-leases")
_ACQUISITION_CLOCK_LOCK = threading.Lock()
_LAST_ACQUISITION_TIMESTAMP = 0.0


class DaemonLeaseError(RuntimeError):
    """Base class for daemon lease failures."""


class DaemonLeaseAmbiguous(DaemonLeaseError):
    """Lease state could not be safely interpreted."""


class DaemonLeaseHeld(DaemonLeaseError):
    """A live lease already exists."""


class DaemonLeaseStale(DaemonLeaseError):
    """A stale lease exists but takeover was not explicitly audited."""


@dataclasses.dataclass(frozen=True)
class DaemonLeasePayload:
    holder_id: str
    pid: int
    host: str
    acquired_at: float
    heartbeat_at: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "holder_id": self.holder_id,
            "pid": self.pid,
            "host": self.host,
            "acquired_at": self.acquired_at,
            "heartbeat_at": self.heartbeat_at,
        }


@dataclasses.dataclass(frozen=True)
class DaemonLease:
    daemon_name: str
    holder_id: str
    lease_path: Path
    payload: DaemonLeasePayload

    def heartbeat(self, *, now: float | None = None) -> None:
        timestamp = _timestamp(now)
        updated = DaemonLeasePayload(
            holder_id=self.payload.holder_id,
            pid=self.payload.pid,
            host=self.payload.host,
            acquired_at=self.payload.acquired_at,
            heartbeat_at=timestamp,
        )
        _write_existing_lease(self.lease_path, updated, expected=self.payload)
        object.__setattr__(self, "payload", updated)

    def release(self) -> None:
        with _operation_lock(self.lease_path, daemon_name=self.daemon_name, wait=True):
            try:
                current = _read_payload(self.lease_path)
            except FileNotFoundError:
                return
            except DaemonLeaseError:
                return
            if _same_acquisition(current, self.payload):
                try:
                    _unlink_lease(self.lease_path)
                except FileNotFoundError:
                    return
                return


def acquire(
    daemon_name: str,
    holder_id: str,
    *,
    state_root: Path | str = DEFAULT_LEASE_ROOT,
    ttl_seconds: float = DEFAULT_LEASE_TTL_SECONDS,
    allow_takeover: bool = False,
    takeover_reason: str | None = None,
    now: float | None = None,
) -> DaemonLease:
    """Acquire a daemon lease or fail closed with a plain-text reason.

    The state root must already exist. Stale lease takeover requires
    ``allow_takeover=True`` and a non-empty ``takeover_reason``; the takeover
    is recorded in an adjacent JSONL audit file before the stale lease is
    replaced.
    """

    if not daemon_name or "/" in daemon_name or daemon_name in {".", ".."}:
        raise DaemonLeaseAmbiguous(f"invalid daemon name for lease path: {daemon_name!r}")
    if not holder_id:
        raise DaemonLeaseAmbiguous("holder_id is required")
    if ttl_seconds <= 0:
        raise DaemonLeaseAmbiguous("ttl_seconds must be positive")

    root = Path(state_root)
    if not root.exists():
        raise DaemonLeaseAmbiguous(f"daemon lease state root is missing: {root}")
    if not root.is_dir():
        raise DaemonLeaseAmbiguous(f"daemon lease state root is not a directory: {root}")

    lease_path = root / f"{daemon_name}.lease"
    with _operation_lock(lease_path, daemon_name=daemon_name, wait=False):
        timestamp = _acquisition_timestamp(now)
        payload = DaemonLeasePayload(
            holder_id=holder_id,
            pid=os.getpid(),
            host=socket.gethostname(),
            acquired_at=timestamp,
            heartbeat_at=timestamp,
        )

        try:
            _atomic_create_lease(lease_path, payload)
            return DaemonLease(daemon_name, holder_id, lease_path, payload)
        except FileExistsError:
            pass

        existing = _read_payload(lease_path)
        if _lease_is_live(existing, ttl_seconds=ttl_seconds, now=timestamp):
            raise DaemonLeaseHeld(
                f"live {daemon_name} lease is held by {existing.holder_id} "
                f"pid={existing.pid} host={existing.host}"
            )

        if not allow_takeover or not takeover_reason:
            raise DaemonLeaseStale(
                f"stale {daemon_name} lease requires explicit audited takeover"
            )

        _takeover_stale_lease(
            lease_path=lease_path,
            daemon_name=daemon_name,
            old_payload=existing,
            new_payload=payload,
            reason=takeover_reason,
            now=timestamp,
        )
        return DaemonLease(daemon_name, holder_id, lease_path, payload)

# The queue-daemon launcher intentionally couples its locked recovery to these
# private seams: _operation_lock, _read_payload, _acquisition_timestamp, and
# _takeover_stale_lease. Preserve their recovery semantics or update that caller.
def _takeover_stale_lease(
    *,
    lease_path: Path,
    daemon_name: str,
    old_payload: DaemonLeasePayload,
    new_payload: DaemonLeasePayload,
    reason: str,
    now: float,
) -> None:
    reread = _read_payload(lease_path)
    if reread != old_payload:
        raise DaemonLeaseHeld(f"{daemon_name} lease changed during takeover")
    record = {
        "daemon_name": daemon_name,
        "action": "daemon_lease_takeover",
        "reason": reason,
        "taken_over_at": now,
        "old": old_payload.as_dict(),
        "new": new_payload.as_dict(),
    }
    audit_path = lease_path.with_suffix(lease_path.suffix + ".takeovers.jsonl")
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    _replace_lease(lease_path, new_payload)


def _atomic_create_lease(path: Path, payload: DaemonLeasePayload) -> None:
    data = json.dumps(payload.as_dict(), sort_keys=True, separators=(",", ":")) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def _replace_lease(path: Path, payload: DaemonLeasePayload) -> None:
    data = json.dumps(payload.as_dict(), sort_keys=True, separators=(",", ":")) + "\n"
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _write_existing_lease(path: Path, payload: DaemonLeasePayload, *, expected: DaemonLeasePayload) -> None:
    with _operation_lock(path, daemon_name=path.stem, wait=True):
        current = _read_payload(path)
        if not _same_acquisition(current, expected):
            raise DaemonLeaseHeld("lease is no longer held by this process")
        _replace_lease(path, payload)
        os.utime(path, (payload.heartbeat_at, payload.heartbeat_at))


def _unlink_lease(path: Path) -> None:
    path.unlink()


@contextmanager
def _operation_lock(
    lease_path: Path,
    *,
    daemon_name: str,
    wait: bool,
) -> Any:
    lock_path = _operation_lock_path(lease_path)
    lock = _LeaseOperationLock(lock_path, daemon_name=daemon_name, wait=wait)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


class _LeaseOperationLock:
    def __init__(self, path: Path, *, daemon_name: str, wait: bool) -> None:
        self.path = path
        self.daemon_name = daemon_name
        self.wait = wait
        self.acquired = False

    def acquire(self) -> None:
        deadline = time.monotonic() + 10.0
        while True:
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError as exc:
                if not self.wait or time.monotonic() >= deadline:
                    raise DaemonLeaseHeld(f"{self.daemon_name} lease operation is in progress") from exc
                time.sleep(0.01)
                continue
            else:
                os.close(fd)
                self.acquired = True
                return

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        self.acquired = False


def _read_payload(path: Path) -> DaemonLeasePayload:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise DaemonLeaseAmbiguous(f"cannot read daemon lease {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DaemonLeaseAmbiguous(f"malformed daemon lease {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DaemonLeaseAmbiguous(f"malformed daemon lease {path}: payload must be an object")
    allowed = {"holder_id", "pid", "host", "acquired_at", "heartbeat_at"}
    if set(data) != allowed:
        raise DaemonLeaseAmbiguous(f"malformed daemon lease {path}: unexpected payload fields")
    try:
        payload = DaemonLeasePayload(
            holder_id=str(data["holder_id"]),
            pid=int(data["pid"]),
            host=str(data["host"]),
            acquired_at=float(data["acquired_at"]),
            heartbeat_at=float(data["heartbeat_at"]),
        )
    except (TypeError, ValueError) as exc:
        raise DaemonLeaseAmbiguous(f"malformed daemon lease {path}: invalid field type") from exc
    if not payload.holder_id or payload.pid <= 0 or not payload.host:
        raise DaemonLeaseAmbiguous(f"malformed daemon lease {path}: invalid identity")
    return payload


def _lease_is_live(payload: DaemonLeasePayload, *, ttl_seconds: float, now: float) -> bool:
    if payload.host == socket.gethostname():
        return _pid_exists(payload.pid)
    # Remote-host liveness is intentionally TTL-only: this host cannot safely
    # prove a foreign PID is alive, so takeover remains gated by heartbeat age.
    return now - payload.heartbeat_at <= ttl_seconds


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        if exc.errno == errno.EPERM:
            return True
        raise DaemonLeaseAmbiguous(f"cannot determine whether pid {pid} is live: {exc}") from exc
    return True


def _same_acquisition(current: DaemonLeasePayload, held: DaemonLeasePayload) -> bool:
    return (
        current.holder_id == held.holder_id
        and current.pid == held.pid
        and current.host == held.host
        and current.acquired_at == held.acquired_at
    )


def _operation_lock_path(lease_path: Path) -> Path:
    return lease_path.with_suffix(lease_path.suffix + ".op.lock")


def _timestamp(now: float | None) -> float:
    return float(time.time() if now is None else now)


def _acquisition_timestamp(now: float | None) -> float:
    global _LAST_ACQUISITION_TIMESTAMP
    timestamp = _timestamp(now)
    with _ACQUISITION_CLOCK_LOCK:
        if timestamp <= _LAST_ACQUISITION_TIMESTAMP:
            timestamp = math.nextafter(_LAST_ACQUISITION_TIMESTAMP, math.inf)
        _LAST_ACQUISITION_TIMESTAMP = timestamp
    return timestamp


__all__ = [
    "DEFAULT_LEASE_ROOT",
    "DEFAULT_LEASE_TTL_SECONDS",
    "DaemonLease",
    "DaemonLeaseAmbiguous",
    "DaemonLeaseError",
    "DaemonLeaseHeld",
    "DaemonLeasePayload",
    "DaemonLeaseStale",
    "acquire",
]
