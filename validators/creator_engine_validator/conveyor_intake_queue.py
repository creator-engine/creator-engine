"""File-backed intake queue for controller-declared, value-free work units.

Claims use a POSIX-atomic :func:`os.replace` rename from ``pending/`` to
``claimed/``.  Concurrent claimers therefore have one winner; a loser sees
``FileNotFoundError`` and continues scanning.  Queue entries contain only
brief SHA pins and declared paths, never credentials or tokens.  A claim grants
no authority beyond the authority already held by its seat.
"""

from __future__ import annotations

import dataclasses
import fcntl
import json
import math
import os
import re
import secrets
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


IntakeStatus = Literal["pending", "claimed", "launching", "done"]
INTAKE_ACTION = "WOULD_DISPATCH"
_UNIT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_BRIEF_SHA_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_RFC3339_Z_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
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
    claim_token: str | None = None
    claim_generation: int = 0
    launch_fenced_at: str | None = None


class IntakeTransitionError(RuntimeError):
    """A durable queue transition failed, with bounded rollback evidence."""

    def __init__(self, action: str, primary: BaseException, rollback: BaseException | None = None) -> None:
        message = f"intake {action} transition failed: {type(primary).__name__}: {primary}"
        if rollback is not None:
            message += f"; rollback failed: {type(rollback).__name__}: {rollback}"
        super().__init__(message)
        self.action = action
        self.primary = primary
        self.rollback = rollback


class IntakeQueueRecordError(ValueError):
    """A pending record could not be safely considered for a claim.

    The path name and underlying exception class are retained as bounded local
    evidence without reflecting record contents or parser error text through
    the seat-facing refusal seam.
    """

    def __init__(self, path: Path, cause: Exception) -> None:
        super().__init__("intake pending record is malformed")
        self.path_name = path.name
        self.cause_type = type(cause).__name__


class _RenameDurabilityError(OSError):
    """A rename completed, but its directory durability confirmation failed."""

    destination_authoritative = True


class _WriteDurabilityError(OSError):
    """A record replacement completed, but directory fsync did not confirm it.

    The target pathname is nevertheless the authoritative observed location.
    Callers which need a definitive outcome must inspect that record rather
    than treating this like a pre-replace write failure.
    """

    destination_authoritative = True


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
            claim_token=None,
            launch_fenced_at=None,
        )
        filename = _unit_filename(pending)
        with _claim_transition_guard(self._unit_lock_path(pending.unit_id)):
            existing = self._publication_record(pending.unit_id)
            if existing is not None:
                location, _path, current = existing
                # Replaying the identical controller publication is a no-op.
                # Any other extant lifecycle record owns this entry; do not
                # rewrite it back to pending or change its payload.
                if location == "pending" and current == pending:
                    return
                raise FileExistsError(
                    f"intake publication already exists in {location}: {filename}"
                )
            _write_unit_atomic(self.pending_dir / filename, pending)

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
        expires_at = _claim_expiry(now, ttl_seconds)
        self._reclaim_stale(now)
        for path in self._ordered_pending_paths():
            try:
                candidate = _read_unit(path)
            except FileNotFoundError:
                continue
            with _claim_transition_guard(self._unit_lock_path(candidate.unit_id)):
                current_record = self._publication_record(candidate.unit_id)
                if current_record is None:
                    continue
                location, current_path, _current = current_record
                if location != "pending" or current_path != path:
                    continue
                claimed_path = self.claimed_dir / path.name
                try:
                    _replace_durable(path, claimed_path)
                except FileNotFoundError:
                    continue
                except OSError as exc:
                    # A failed post-rename fsync means the claimed location is
                    # authoritative.  Put its still-pending record back before
                    # reporting the bounded claim failure; never manufacture a
                    # second source record beside it.
                    rollback_error = _restore_rename(claimed_path, path) if _destination_is_authoritative(
                        path, claimed_path, exc
                    ) else None
                    raise IntakeTransitionError("claim", exc, rollback_error) from exc
                try:
                    original = _read_unit(claimed_path)
                    if original.status != "pending":
                        raise ValueError("pending queue path did not contain a pending unit")
                    unit = dataclasses.replace(
                        original,
                        status="claimed",
                        claimed_by=clean_claimer,
                        claimed_at=now,
                        claim_expires_at=expires_at,
                        claim_token=secrets.token_hex(32),
                        claim_generation=original.claim_generation + 1,
                        launch_fenced_at=None,
                    )
                    _write_unit_atomic(claimed_path, unit)
                except _WriteDurabilityError as exc:
                    # ``os.replace`` already installed the new claimed
                    # payload.  Never move that payload back to pending just
                    # because the following directory fsync was uncertain:
                    # inspect the authoritative path and use it if intact.
                    try:
                        published = _read_unit(claimed_path)
                    except (OSError, ValueError) as read_exc:
                        raise IntakeTransitionError("claim", exc, read_exc) from exc
                    if published != unit:
                        raise IntakeTransitionError("claim", exc) from exc
                except (OSError, ValueError) as exc:
                    rollback_error = _restore_rename(claimed_path, path)
                    if isinstance(exc, ValueError) and rollback_error is None:
                        continue
                    raise IntakeTransitionError("claim", exc, rollback_error) from exc
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
        claim_token: str,
        claim_generation: int,
        clock: IntakeClock | None = None,
    ) -> None:
        """Complete the exact owned claim generation, never a same-seat successor."""
        self._complete(
            unit_id,
            claimer=_required_str({"claimer": claimer}, "claimer"),
            claim_token=claim_token,
            claim_generation=claim_generation,
            clock=clock,
        )

    def release_entry(
        self,
        unit_id: str,
        claimer: str,
        *,
        claim_token: str | None = None,
        clock: IntakeClock | None = None,
    ) -> None:
        self._ensure_dirs()
        claimed_path = self._claimed_path_for_unit(unit_id)
        if claimed_path is None:
            raise FileNotFoundError(f"claimed intake unit not found: {unit_id}")
        clean_claimer = _required_str({"claimer": claimer}, "claimer")
        with _claim_transition_guard(self._unit_lock_path(unit_id)):
            claimed_path = self._claimed_path_for_unit(unit_id)
            if claimed_path is None:
                raise FileNotFoundError(f"claimed intake unit not found: {unit_id}")
            try:
                claimed = _read_unit(claimed_path)
            except FileNotFoundError as exc:
                raise FileNotFoundError(f"claimed intake unit not found: {unit_id}") from exc
            if claimed.claimed_by != clean_claimer:
                raise PermissionError(f"intake unit {unit_id!r} is not claimed by {clean_claimer!r}")
            _require_claim_token(claimed, claim_token)
            if claimed.status not in {"claimed", "launching"}:
                raise ValueError(f"intake unit {unit_id!r} is not releasable from {claimed.status!r}")
            unit = dataclasses.replace(
                claimed,
                status="pending",
                claimed_by=None,
                claimed_at=None,
                claim_expires_at=None,
                claim_token=None,
                launch_fenced_at=None,
            )
            pending_path = self.pending_dir / claimed_path.name
            try:
                _write_unit_atomic(claimed_path, unit)
            except OSError as exc:
                raise IntakeTransitionError("release", exc) from exc
            try:
                _replace_durable(claimed_path, pending_path)
            except OSError as exc:
                if _destination_is_authoritative(claimed_path, pending_path, exc):
                    # The pending record won the rename despite a failed
                    # directory fsync.  It is authoritative; recreating the
                    # claimed source here would split the queue.
                    pass
                else:
                    rollback_error: BaseException | None = None
                    try:
                        _write_unit_atomic(claimed_path, claimed)
                    except OSError as rollback_exc:
                        rollback_error = rollback_exc
                    raise IntakeTransitionError("release", exc, rollback_error) from exc
        self._append_ledger("released", unit, clean_claimer, _clock_now(clock))

    def fence_launch(
        self,
        unit_id: str,
        claimer: str,
        claim_token: str,
        *,
        clock: IntakeClock | None = None,
    ) -> IntakeUnit:
        """Atomically make an unexpired owned claim non-reclaimable for launch.

        A ``launching`` record is deliberately excluded from stale reclaim.  A
        launcher therefore has one durable winner while it crosses the external
        governed-launch seam; a later seat cannot reclaim the same unit.
        """
        self._ensure_dirs()
        now = _clock_now(clock)
        claimed_path = self._claimed_path_for_unit(unit_id)
        if claimed_path is None:
            raise FileNotFoundError(f"claimed intake unit not found: {unit_id}")
        clean_claimer = _required_str({"claimer": claimer}, "claimer")
        with _claim_transition_guard(self._unit_lock_path(unit_id)):
            claimed_path = self._claimed_path_for_unit(unit_id)
            if claimed_path is None:
                raise FileNotFoundError(f"claimed intake unit not found: {unit_id}")
            try:
                claimed = _read_unit(claimed_path)
            except FileNotFoundError as exc:
                raise FileNotFoundError(f"claimed intake unit not found: {unit_id}") from exc
            if claimed.status != "claimed" or claimed.claimed_by != clean_claimer:
                raise PermissionError(f"intake unit {unit_id!r} is not an active claim of {clean_claimer!r}")
            _require_claim_token(claimed, claim_token)
            if claimed.claim_expires_at is None:
                raise ValueError("seat launch requires a finite claim TTL")
            if _parse_rfc3339_z(claimed.claim_expires_at, "claim_expires_at") <= _parse_rfc3339_z(now, "clock"):
                raise PermissionError("intake claim expired before launch fence")
            fenced = dataclasses.replace(claimed, status="launching", launch_fenced_at=now)
            try:
                _write_unit_atomic(claimed_path, fenced)
            except OSError as exc:
                raise IntakeTransitionError("launch_fence", exc) from exc
        self._append_ledger("launch_fenced", fenced, clean_claimer, now)
        return fenced

    def _complete(
        self,
        unit_id: str,
        *,
        claimer: str | None,
        claim_token: str | None = None,
        claim_generation: int | None = None,
        clock: IntakeClock | None = None,
    ) -> None:
        self._ensure_dirs()
        claimed_path = self._claimed_path_for_unit(unit_id)
        if claimed_path is None:
            raise FileNotFoundError(f"claimed intake unit not found: {unit_id}")
        with _claim_transition_guard(self._unit_lock_path(unit_id)):
            claimed_path = self._claimed_path_for_unit(unit_id)
            if claimed_path is None:
                raise FileNotFoundError(f"claimed intake unit not found: {unit_id}")
            try:
                claimed = _read_unit(claimed_path)
            except FileNotFoundError as exc:
                raise FileNotFoundError(f"claimed intake unit not found: {unit_id}") from exc
            if claimer is not None:
                if claimed.claimed_by != claimer:
                    raise PermissionError(f"intake unit {unit_id!r} is not claimed by {claimer!r}")
                _require_claim_token(claimed, claim_token)
                _require_claim_generation(claimed, claim_generation)
            unit = dataclasses.replace(claimed, status="done")
            done_path = self.done_dir / claimed_path.name
            try:
                _write_unit_atomic(claimed_path, unit)
            except OSError as exc:
                raise IntakeTransitionError("complete", exc) from exc
            try:
                _replace_durable(claimed_path, done_path)
            except OSError as exc:
                if not _destination_is_authoritative(claimed_path, done_path, exc):
                    rollback_error: BaseException | None = None
                    try:
                        _write_unit_atomic(claimed_path, claimed)
                    except OSError as rollback_exc:
                        rollback_error = rollback_exc
                    raise IntakeTransitionError("complete", exc, rollback_error) from exc
        self._append_ledger("completed", unit, claimer or unit.claimed_by or "controller", _clock_now(clock))

    def _reclaim_stale(self, now: str) -> None:
        current = _parse_rfc3339_z(now, "clock")
        for claimed_path in sorted(self.claimed_dir.iterdir()):
            if not claimed_path.is_file() or claimed_path.suffix not in _SUPPORTED_SUFFIXES:
                continue
            try:
                candidate = _read_unit(claimed_path)
                with _claim_transition_guard(self._unit_lock_path(candidate.unit_id)):
                    current_record = self._publication_record(candidate.unit_id)
                    if current_record is None:
                        continue
                    location, current_path, _current = current_record
                    if location != "claimed" or current_path != claimed_path:
                        continue
                    try:
                        unit = _read_unit(claimed_path)
                    except FileNotFoundError:
                        continue
                    if unit.status != "claimed" or unit.claim_expires_at is None:
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
                        claim_token=None,
                        launch_fenced_at=None,
                    )
                    try:
                        _write_unit_atomic(claimed_path, reclaimed)
                        _replace_durable(claimed_path, pending_path)
                    except OSError as exc:
                        if not _destination_is_authoritative(claimed_path, pending_path, exc):
                            rollback_error: BaseException | None = None
                            try:
                                _write_unit_atomic(claimed_path, unit)
                            except OSError as rollback_exc:
                                rollback_error = rollback_exc
                            raise IntakeTransitionError("stale_reclaim", exc, rollback_error) from exc
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
        self._recover_stranded_locations()

    def _recover_stranded_locations(self) -> None:
        """Finish queue-owned rename/state windows left by a dead process.

        A transition deliberately writes its new record *at the old location*
        before moving it.  A process death can therefore leave a ``pending``
        or ``done`` record in ``claimed/``.  Recover those two unambiguous
        states before any selection/reclaim scan so a pending unit never becomes
        invisible.  Other location/status combinations were not emitted by a
        queue transition and are refused rather than guessed at.
        """
        for path in sorted(self.claimed_dir.iterdir()):
            if not path.is_file() or path.suffix not in _SUPPORTED_SUFFIXES:
                continue
            unit = _read_unit(path)
            if unit.status in {"claimed", "launching"}:
                continue
            if unit.status not in {"pending", "done"}:
                raise IntakeTransitionError(
                    "recovery", ValueError(f"claimed record has incompatible {unit.status!r} state")
                )
            destination = (self.pending_dir if unit.status == "pending" else self.done_dir) / path.name
            with _claim_transition_guard(self._unit_lock_path(unit.unit_id)):
                current_record = self._publication_record(unit.unit_id)
                if current_record is None:
                    continue
                location, current_path, _current = current_record
                if location != "claimed" or current_path != path:
                    continue
                # Another recovery/transition may have completed while the
                # lock was acquired; only move the exact stranded state.
                try:
                    current = _read_unit(path)
                except FileNotFoundError:
                    continue
                if current.status != unit.status:
                    continue
                if destination.exists():
                    raise IntakeTransitionError(
                        "recovery", FileExistsError(f"refusing duplicate recovery destination: {destination}")
                    )
                try:
                    _replace_durable(path, destination)
                except OSError as exc:
                    if not _destination_is_authoritative(path, destination, exc):
                        raise IntakeTransitionError("recovery", exc) from exc

    def _claimed_path_for_unit(self, unit_id: str) -> Path | None:
        record = self._publication_record(unit_id)
        if record is None:
            return None
        location, path, _unit = record
        return path if location == "claimed" else None

    def _unit_lock_path(self, unit_id: str) -> Path:
        if not _UNIT_ID_PATTERN.fullmatch(unit_id):
            raise ValueError("intake unit_id must contain only letters, digits, '.', '_', or '-'")
        return self.root / f".{unit_id}.transition-lock"

    def _publication_record(self, unit_id: str) -> tuple[str, Path, IntakeUnit] | None:
        """Return the sole lifecycle record for a stable unit identity.

        A unit may be serialized under either supported suffix and its priority
        prefix can change between controller publications.  The record lookup
        therefore follows the payload's immutable ``unit_id``, never a sorted
        filename.  More than one matching lifecycle record is split-brain, not
        an invitation to select an arbitrary generation.
        """
        records: list[tuple[str, Path, IntakeUnit]] = []
        for location, directory in (
            ("pending", self.pending_dir),
            ("claimed", self.claimed_dir),
            ("done", self.done_dir),
        ):
            for path in sorted(directory.iterdir()):
                if not path.is_file() or path.suffix not in _SUPPORTED_SUFFIXES:
                    continue
                try:
                    current = _read_unit(path)
                except FileNotFoundError:
                    continue
                if current.unit_id == unit_id:
                    records.append((location, path, current))
        if len(records) > 1:
            raise IntakeTransitionError(
                "lifecycle_lookup", ValueError(f"intake publication has duplicate lifecycle records: {unit_id}")
            )
        return records[0] if records else None

    def _ordered_pending_paths(self) -> list[Path]:
        """Return pending entries in numeric priority order or refuse the scan.

        Queue filenames historically used a minimum-width decimal prefix.  Keep
        accepting those files, but do not let lexical filename ordering invert
        priorities at six digits.  A malformed or schema-invalid pending record
        is controller queue state, not an absent unit: silently skipping it
        could make a seat report an empty queue while work needs reconciliation.
        Refuse the bounded claim attempt instead.
        """
        candidates: list[tuple[int, str, Path]] = []
        for path in sorted(self.pending_dir.iterdir()):
            if not path.is_file() or path.suffix not in _SUPPORTED_SUFFIXES:
                continue
            try:
                priority = _read_unit(path).priority
            except FileNotFoundError:
                continue
            except Exception as exc:
                raise IntakeQueueRecordError(path, exc) from exc
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
        try:
            _fsync_directory(path.parent)
        except OSError as exc:
            raise _WriteDurabilityError(*exc.args) from exc
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
        claim_token=_optional_claim_token(data),
        claim_generation=_claim_generation(data),
        launch_fenced_at=_optional_rfc3339_z(data, "launch_fenced_at"),
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
        ("launch_fenced_at", unit.launch_fenced_at),
    ):
        if value is not None and (not isinstance(value, str) or not value):
            raise ValueError(f"intake unit {name} must be a non-empty string or null")
    if unit.claimed_at is not None:
        _parse_rfc3339_z(unit.claimed_at, "claimed_at")
    if unit.claim_expires_at is not None:
        _parse_rfc3339_z(unit.claim_expires_at, "claim_expires_at")
    if unit.claim_token is not None and not re.fullmatch(r"[0-9a-f]{64}", unit.claim_token):
        raise ValueError("intake unit claim_token must be a 64-hex token or null")
    if isinstance(unit.claim_generation, bool) or not isinstance(unit.claim_generation, int) or unit.claim_generation < 0:
        raise ValueError("intake unit claim_generation must be a non-negative integer")
    if unit.status == "pending" and any((unit.claimed_by, unit.claimed_at, unit.claim_expires_at, unit.claim_token, unit.launch_fenced_at)):
        raise ValueError("pending intake unit must not retain claim fields")
    if unit.status in {"claimed", "launching"} and (not unit.claimed_by or not unit.claimed_at or not unit.claim_token):
        raise ValueError(f"{unit.status} intake unit requires ownership fields")
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
    if status not in {"pending", "claimed", "launching", "done"}:
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


def _optional_claim_token(data: Mapping[str, object]) -> str | None:
    value = _optional_str(data, "claim_token")
    if value is not None and not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("intake unit claim_token must be a 64-hex token or null")
    return value


def _claim_generation(data: Mapping[str, object]) -> int:
    value = data.get("claim_generation", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("intake unit claim_generation must be a non-negative integer")
    return value


def _require_claim_token(unit: IntakeUnit, provided: str | None) -> None:
    if not isinstance(provided, str) or unit.claim_token is None or not secrets.compare_digest(unit.claim_token, provided):
        raise PermissionError("intake claim token does not match current ownership")


def _require_claim_generation(unit: IntakeUnit, provided: int | None) -> None:
    if isinstance(provided, bool) or not isinstance(provided, int) or unit.claim_generation != provided:
        raise PermissionError("intake claim generation does not match current ownership")


def _restore_rename(source: Path, destination: Path) -> BaseException | None:
    try:
        _replace_durable(source, destination)
    except OSError as exc:
        return exc
    return None


def _destination_is_authoritative(source: Path, destination: Path, exc: BaseException) -> bool:
    """Return whether a failed durable rename already published ``destination``."""
    return (
        isinstance(exc, _RenameDurabilityError)
        and exc.destination_authoritative
        and not source.exists()
        and destination.exists()
    )


def _replace_durable(source: Path, destination: Path) -> None:
    """Rename and persist the containing directories before reporting success."""
    os.replace(source, destination)
    try:
        _fsync_directory(destination.parent)
        if source.parent != destination.parent:
            _fsync_directory(source.parent)
    except OSError as exc:
        raise _RenameDurabilityError(*exc.args) from exc


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _clock_now(clock: IntakeClock | None) -> str:
    value = clock() if clock is not None else _format_rfc3339_z(datetime.now(UTC))
    if not isinstance(value, str):
        raise ValueError("intake queue clock must return an RFC 3339 UTC Z string")
    _parse_rfc3339_z(value, "clock")
    return value


def _parse_rfc3339_z(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not _RFC3339_Z_PATTERN.fullmatch(value):
        raise ValueError(f"intake unit {field} must be RFC 3339 UTC with Z suffix")
    try:
        format_string = "%Y-%m-%dT%H:%M:%S.%fZ" if "." in value else "%Y-%m-%dT%H:%M:%SZ"
        return datetime.strptime(value, format_string).replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"intake unit {field} must be RFC 3339 UTC with Z suffix") from exc


def _format_rfc3339_z(value: datetime) -> str:
    """Serialize UTC timestamps without discarding representable precision."""
    value = value.astimezone(UTC)
    whole_seconds = value.strftime("%Y-%m-%dT%H:%M:%S")
    if value.microsecond:
        return f"{whole_seconds}.{value.microsecond:06d}".rstrip("0") + "Z"
    return whole_seconds + "Z"


def _claim_expiry(now: str, ttl_seconds: float | int | None) -> str | None:
    if ttl_seconds is None:
        return None
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float)):
        raise ValueError("claim ttl_seconds must be a finite number")
    seconds = float(ttl_seconds)
    if not math.isfinite(seconds) or not _MIN_CLAIM_TTL_SECONDS <= seconds <= _MAX_CLAIM_TTL_SECONDS:
        raise ValueError(f"claim ttl_seconds must be finite and in 0 < t <= {_MAX_CLAIM_TTL_SECONDS}")
    try:
        expires_at = _parse_rfc3339_z(now, "clock") + timedelta(seconds=seconds)
    except OverflowError as exc:
        raise ValueError("claim ttl_seconds overflows the clock") from exc
    return _format_rfc3339_z(expires_at)


class _claim_transition_guard:
    """Serialize every transition of one claim file on a stable POSIX lock inode."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    def __enter__(self) -> "_claim_transition_guard":
        self._fd = os.open(self._path, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


_SERIALIZATION_SUFFIX = ".yaml" if yaml is not None else ".json"
_SUPPORTED_SUFFIXES = (".yaml", ".json")
_MAX_CLAIM_TTL_SECONDS = 3600
_MIN_CLAIM_TTL_SECONDS = 0.000001
