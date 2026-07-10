"""File-backed intake queue for controller-declared, value-free work units.

Claims use a POSIX-atomic :func:`os.replace` rename from ``pending/`` to
``claimed/``.  Concurrent claimers therefore have one winner; a loser sees
``FileNotFoundError`` and continues scanning.  Queue entries contain only
brief SHA pins and declared paths, never credentials or tokens.  A claim grants
no authority beyond the authority already held by its seat.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

try:  # pragma: no cover - fallback covered only in images without PyYAML.
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


IntakeStatus = Literal["pending", "claimed", "done"]
INTAKE_ACTION = "WOULD_DISPATCH"
_UNIT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_BRIEF_SHA_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
IntakeReadErrorSink = Callable[[Path, Exception], None]
IntakeClock = Callable[[], str]


@dataclass(frozen=True)
class IntakeUnit:
    unit_id: str
    brief_ref: str
    branch: str
    worktree: str
    priority: int
    work_class: str
    status: IntakeStatus
    created_at: str
    brief_sha: str
    territory_paths: tuple[str, ...]
    claimed_by: str | None = None
    claimed_at: str | None = None
    claim_expires_at: str | None = None


@dataclass(frozen=True)
class IntakeDispatchPlan:
    seat_id: str
    unit: IntakeUnit
    action: str = INTAKE_ACTION


class IntakeQueue:
    """Atomic file queue with pending, claimed, and done state directories."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.pending_dir = self.root / "pending"
        self.claimed_dir = self.root / "claimed"
        self.done_dir = self.root / "done"
        self.ledger_path = self.root / "intake-claims.jsonl"

    def stock(self, unit: IntakeUnit) -> None:
        self._ensure_dirs()
        pending = dataclasses.replace(
            unit,
            status="pending",
            claimed_by=None,
            claimed_at=None,
            claim_expires_at=None,
        )
        _write_unit_atomic(self.pending_dir / _unit_filename(pending), pending)

    def publish_entry(self, unit: IntakeUnit) -> None:
        """Publish ``unit`` to pending; compatibility alias for :meth:`stock`."""
        self.stock(unit)

    def claim_next(self) -> IntakeUnit | None:
        """Claim the next item as the legacy controller identity, without expiry."""
        return self.claim_entry("controller")

    def claim_entry(
        self,
        claimer: str,
        *,
        ttl_seconds: float | int | None = None,
        clock: IntakeClock | None = None,
    ) -> IntakeUnit | None:
        self._ensure_dirs()
        clean_claimer = _required_str({"claimer": claimer}, "claimer")
        now = _clock_now(clock)
        self._reclaim_stale(now)
        for path in self._ordered_pending_paths():
            claimed_path = self.claimed_dir / path.name
            try:
                os.replace(path, claimed_path)
            except FileNotFoundError:
                continue
            expires_at = _claim_expiry(now, ttl_seconds)
            unit = dataclasses.replace(
                _read_unit(claimed_path),
                status="claimed",
                claimed_by=clean_claimer,
                claimed_at=now,
                claim_expires_at=expires_at,
            )
            _write_unit_atomic(claimed_path, unit)
            self._append_ledger("claimed", unit, clean_claimer, now)
            return unit
        return None

    def list_pending(
        self,
        *,
        read_error_sink: IntakeReadErrorSink | None = None,
    ) -> list[IntakeUnit]:
        self._ensure_dirs()
        units: list[tuple[IntakeUnit, str]] = []
        for path in self.pending_dir.iterdir():
            if path.is_file() and path.suffix in _SUPPORTED_SUFFIXES:
                try:
                    units.append((_read_unit(path), path.name))
                except Exception as exc:
                    if read_error_sink is not None:
                        read_error_sink(path, exc)
        return [unit for unit, _name in sorted(units, key=lambda item: (item[0].priority, item[1]))]

    def list_open(
        self,
        *,
        read_error_sink: IntakeReadErrorSink | None = None,
    ) -> list[IntakeUnit]:
        """List pending work; compatibility alias for :meth:`list_pending`."""
        return self.list_pending(read_error_sink=read_error_sink)

    def mark_done(self, unit_id: str) -> None:
        """Complete an entry without an ownership check for legacy callers."""
        self._complete(unit_id, claimer=None)

    def complete_entry(
        self,
        unit_id: str,
        claimer: str,
        *,
        clock: IntakeClock | None = None,
    ) -> None:
        """Complete a claimed entry, refusing a claimer other than its owner."""
        self._complete(unit_id, claimer=_required_str({"claimer": claimer}, "claimer"), clock=clock)

    def release_entry(
        self,
        unit_id: str,
        claimer: str,
        *,
        clock: IntakeClock | None = None,
    ) -> None:
        self._ensure_dirs()
        claimed_path = self._claimed_path_for_unit(unit_id)
        if claimed_path is None:
            raise FileNotFoundError(f"claimed intake unit not found: {unit_id}")
        clean_claimer = _required_str({"claimer": claimer}, "claimer")
        claimed = _read_unit(claimed_path)
        if claimed.claimed_by != clean_claimer:
            raise PermissionError(f"intake unit {unit_id!r} is not claimed by {clean_claimer!r}")
        unit = dataclasses.replace(
            claimed,
            status="pending",
            claimed_by=None,
            claimed_at=None,
            claim_expires_at=None,
        )
        pending_path = self.pending_dir / claimed_path.name
        _write_unit_atomic(claimed_path, unit)
        os.replace(claimed_path, pending_path)
        self._append_ledger("released", unit, clean_claimer, _clock_now(clock))

    def _complete(
        self,
        unit_id: str,
        *,
        claimer: str | None,
        clock: IntakeClock | None = None,
    ) -> None:
        self._ensure_dirs()
        claimed_path = self._claimed_path_for_unit(unit_id)
        if claimed_path is None:
            raise FileNotFoundError(f"claimed intake unit not found: {unit_id}")
        claimed = _read_unit(claimed_path)
        if claimer is not None and claimed.claimed_by != claimer:
            raise PermissionError(f"intake unit {unit_id!r} is not claimed by {claimer!r}")
        unit = dataclasses.replace(claimed, status="done")
        done_path = self.done_dir / claimed_path.name
        _write_unit_atomic(claimed_path, unit)
        os.replace(claimed_path, done_path)
        self._append_ledger("completed", unit, claimer or unit.claimed_by or "controller", _clock_now(clock))

    def _reclaim_stale(self, now: str) -> None:
        current = _parse_rfc3339_z(now, "clock")
        for claimed_path in sorted(self.claimed_dir.iterdir()):
            if not claimed_path.is_file() or claimed_path.suffix not in _SUPPORTED_SUFFIXES:
                continue
            try:
                with _reclaim_guard(self.root / f".{claimed_path.name}.reclaim"):
                    try:
                        unit = _read_unit(claimed_path)
                    except FileNotFoundError:
                        continue
                    if unit.claim_expires_at is None:
                        continue
                    if _parse_rfc3339_z(unit.claim_expires_at, "claim_expires_at") > current:
                        continue
                    pending_path = self.pending_dir / claimed_path.name
                    reclaimed = dataclasses.replace(
                        unit,
                        status="pending",
                        claimed_by=None,
                        claimed_at=None,
                        claim_expires_at=None,
                    )
                    _write_unit_atomic(claimed_path, reclaimed)
                    os.replace(claimed_path, pending_path)
            except (FileExistsError, FileNotFoundError):
                continue
            self._append_ledger("stale_reclaim", reclaimed, unit.claimed_by or "unknown", now)

    def _append_ledger(self, action: str, unit: IntakeUnit, claimer: str, ts: str) -> None:
        record = {
            "action": action,
            "unit_id": unit.unit_id,
            "claimer": claimer,
            "brief_sha": unit.brief_sha,
            "ts": ts,
        }
        try:
            with self.ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        except OSError as exc:
            print(f"conveyor-intake ledger append failed: {exc}", file=sys.stderr)

    def _ensure_dirs(self) -> None:
        for path in (self.pending_dir, self.claimed_dir, self.done_dir):
            path.mkdir(parents=True, exist_ok=True)

    def _claimed_path_for_unit(self, unit_id: str) -> Path | None:
        for path in sorted(self.claimed_dir.iterdir()):
            if path.is_file() and path.suffix in _SUPPORTED_SUFFIXES and _read_unit(path).unit_id == unit_id:
                return path
        return None

    def _ordered_pending_paths(self) -> list[Path]:
        """Return only valid pending entries in numeric priority order.

        Queue filenames historically used a minimum-width decimal prefix.  Keep
        accepting those files, but do not let lexical filename ordering invert
        priorities at six digits.  Invalid priority values are deliberately not
        candidates for claim; reading them through ``list_pending`` still makes
        their validation error observable to callers with an error sink.
        """
        candidates: list[tuple[int, str, Path]] = []
        for path in self.pending_dir.iterdir():
            if not path.is_file() or path.suffix not in _SUPPORTED_SUFFIXES:
                continue
            try:
                priority = _read_unit(path).priority
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
            candidates.append((priority, path.name, path))
        return [path for _priority, _name, path in sorted(candidates)]


class IntakeQueueReader:
    """Produce dry-run dispatch plans without claiming queue entries."""

    def __init__(
        self,
        queue: IntakeQueue,
        seat_probe_results: Mapping[str, bool],
        *,
        read_error_sink: IntakeReadErrorSink | None = None,
    ) -> None:
        self.queue = queue
        self.seat_probe_results = dict(seat_probe_results)
        self.read_error_sink = read_error_sink

    def __iter__(self) -> Iterator[IntakeDispatchPlan]:
        pending_units = iter(self.queue.list_pending(read_error_sink=self.read_error_sink))
        for seat_id, had_ready_signal in self.seat_probe_results.items():
            if had_ready_signal:
                continue
            try:
                unit = next(pending_units)
            except StopIteration:
                return
            yield IntakeDispatchPlan(seat_id=seat_id, unit=unit)


def _unit_filename(unit: IntakeUnit) -> str:
    priority = _required_priority(unit.priority)
    if not _UNIT_ID_PATTERN.fullmatch(unit.unit_id):
        raise ValueError("intake unit_id must contain only letters, digits, '.', '_', or '-'")
    return f"{priority:05d}-{unit.unit_id}{_SERIALIZATION_SUFFIX}"


def _write_unit_atomic(path: Path, unit: IntakeUnit) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _dump_unit(unit)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _read_unit(path: Path) -> IntakeUnit:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(raw)
    elif yaml is not None:
        data = yaml.safe_load(raw)
    else:  # pragma: no cover - only possible for hand-authored .yaml without PyYAML.
        raise RuntimeError("PyYAML is required to read YAML intake units")
    if not isinstance(data, Mapping):
        raise ValueError(f"intake unit file must contain a mapping: {path}")
    return IntakeUnit(
        unit_id=_required_str(data, "unit_id"),
        brief_ref=_required_str(data, "brief_ref"),
        branch=_required_str(data, "branch"),
        worktree=_required_str(data, "worktree"),
        priority=_required_priority(data.get("priority")),
        work_class=_required_str(data, "work_class"),
        status=_required_status(data),
        created_at=_required_str(data, "created_at"),
        brief_sha=_required_brief_sha(data),
        territory_paths=_territory_paths(data),
        claimed_by=_optional_str(data, "claimed_by"),
        claimed_at=_optional_rfc3339_z(data, "claimed_at"),
        claim_expires_at=_optional_rfc3339_z(data, "claim_expires_at"),
    )


def _dump_unit(unit: IntakeUnit) -> str:
    if not _BRIEF_SHA_PATTERN.fullmatch(unit.brief_sha):
        raise ValueError("intake unit brief_sha must be a lowercase 40- or 64-hex SHA")
    _required_priority(unit.priority)
    if any(not isinstance(path, str) for path in unit.territory_paths):
        raise ValueError("intake unit territory_paths must be a sequence of strings")
    for name, value in (
        ("claimed_by", unit.claimed_by),
        ("claimed_at", unit.claimed_at),
        ("claim_expires_at", unit.claim_expires_at),
    ):
        if value is not None and (not isinstance(value, str) or not value):
            raise ValueError(f"intake unit {name} must be a non-empty string or null")
    if unit.claimed_at is not None:
        _parse_rfc3339_z(unit.claimed_at, "claimed_at")
    if unit.claim_expires_at is not None:
        _parse_rfc3339_z(unit.claim_expires_at, "claim_expires_at")
    data = dataclasses.asdict(unit)
    if yaml is not None:
        return yaml.safe_dump(data, sort_keys=True)
    return json.dumps(data, sort_keys=True, indent=2) + "\n"


def _required_str(data: Mapping[str, object], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"intake unit requires non-empty string field: {name}")
    return value


def _required_status(data: Mapping[str, object]) -> IntakeStatus:
    status = _required_str(data, "status")
    if status not in {"pending", "claimed", "done"}:
        raise ValueError(f"invalid intake unit status: {status}")
    return status  # type: ignore[return-value]


def _required_priority(value: object) -> int:
    """Accept only non-negative integer priorities (never bools or floats)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("intake unit priority must be a non-negative integer")
    return value


def _required_brief_sha(data: Mapping[str, object]) -> str:
    value = _required_str(data, "brief_sha")
    if not _BRIEF_SHA_PATTERN.fullmatch(value):
        raise ValueError("intake unit brief_sha must be a lowercase 40- or 64-hex SHA")
    return value


def _territory_paths(data: Mapping[str, object]) -> tuple[str, ...]:
    value = data.get("territory_paths")
    if not isinstance(value, (list, tuple)) or any(not isinstance(path, str) for path in value):
        raise ValueError("intake unit territory_paths must be a sequence of strings")
    return tuple(value)


def _optional_str(data: Mapping[str, object], name: str) -> str | None:
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"intake unit {name} must be a non-empty string or null")
    return value


def _optional_rfc3339_z(data: Mapping[str, object], name: str) -> str | None:
    value = _optional_str(data, name)
    if value is not None:
        _parse_rfc3339_z(value, name)
    return value


def _clock_now(clock: IntakeClock | None) -> str:
    value = clock() if clock is not None else datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not isinstance(value, str):
        raise ValueError("intake queue clock must return an RFC 3339 UTC Z string")
    _parse_rfc3339_z(value, "clock")
    return value


def _parse_rfc3339_z(value: str, field: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"intake unit {field} must be RFC 3339 UTC with Z suffix") from exc


def _claim_expiry(now: str, ttl_seconds: float | int | None) -> str | None:
    if ttl_seconds is None:
        return None
    seconds = float(ttl_seconds)
    if seconds <= 0:
        raise ValueError("claim ttl_seconds must be positive")
    return (_parse_rfc3339_z(now, "clock") + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


class _reclaim_guard:
    """Serialize stale reclaim of one claim file using an exclusive local marker."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    def __enter__(self) -> "_reclaim_guard":
        self._fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass


_SERIALIZATION_SUFFIX = ".yaml" if yaml is not None else ".json"
_SUPPORTED_SUFFIXES = (".yaml", ".json")
