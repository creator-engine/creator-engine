"""File-backed dry-run intake queue for conveyor work units."""

from __future__ import annotations

import dataclasses
import json
import os
import re
import tempfile
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:  # pragma: no cover - fallback covered only in images without PyYAML.
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


IntakeStatus = Literal["pending", "claimed", "done"]
INTAKE_ACTION = "WOULD_DISPATCH"
_UNIT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
IntakeReadErrorSink = Callable[[Path, Exception], None]


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

    def stock(self, unit: IntakeUnit) -> None:
        self._ensure_dirs()
        pending = dataclasses.replace(unit, status="pending")
        _write_unit_atomic(self.pending_dir / _unit_filename(pending), pending)

    def claim_next(self) -> IntakeUnit | None:
        self._ensure_dirs()
        for path in sorted(self.pending_dir.iterdir()):
            if not path.is_file() or path.suffix not in _SUPPORTED_SUFFIXES:
                continue
            claimed_path = self.claimed_dir / path.name
            try:
                os.replace(path, claimed_path)
            except FileNotFoundError:
                continue
            unit = dataclasses.replace(_read_unit(claimed_path), status="claimed")
            _write_unit_atomic(claimed_path, unit)
            return unit
        return None

    def list_pending(
        self,
        *,
        read_error_sink: IntakeReadErrorSink | None = None,
    ) -> list[IntakeUnit]:
        self._ensure_dirs()
        units: list[IntakeUnit] = []
        for path in sorted(self.pending_dir.iterdir()):
            if path.is_file() and path.suffix in _SUPPORTED_SUFFIXES:
                try:
                    units.append(_read_unit(path))
                except Exception as exc:
                    if read_error_sink is not None:
                        read_error_sink(path, exc)
        return units

    def mark_done(self, unit_id: str) -> None:
        self._ensure_dirs()
        claimed_path = self._claimed_path_for_unit(unit_id)
        if claimed_path is None:
            raise FileNotFoundError(f"claimed intake unit not found: {unit_id}")
        unit = dataclasses.replace(_read_unit(claimed_path), status="done")
        done_path = self.done_dir / claimed_path.name
        _write_unit_atomic(claimed_path, unit)
        os.replace(claimed_path, done_path)

    def _ensure_dirs(self) -> None:
        for path in (self.pending_dir, self.claimed_dir, self.done_dir):
            path.mkdir(parents=True, exist_ok=True)

    def _claimed_path_for_unit(self, unit_id: str) -> Path | None:
        for path in sorted(self.claimed_dir.iterdir()):
            if path.is_file() and path.suffix in _SUPPORTED_SUFFIXES and _read_unit(path).unit_id == unit_id:
                return path
        return None


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
    if unit.priority < 0:
        raise ValueError("intake unit priority must be non-negative")
    if not _UNIT_ID_PATTERN.fullmatch(unit.unit_id):
        raise ValueError("intake unit_id must contain only letters, digits, '.', '_', or '-'")
    return f"{unit.priority:05d}-{unit.unit_id}{_SERIALIZATION_SUFFIX}"


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
        priority=int(data["priority"]),
        work_class=_required_str(data, "work_class"),
        status=_required_status(data),
        created_at=_required_str(data, "created_at"),
    )


def _dump_unit(unit: IntakeUnit) -> str:
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


_SERIALIZATION_SUFFIX = ".yaml" if yaml is not None else ".json"
_SUPPORTED_SUFFIXES = (".yaml", ".json")
