"""Active-Work Ledger cross-record conflict validation (PCO Slice 1/2).

This check sits above ``active_work_ledger_schema``.  The schema check
continues to validate one record at a time; this module validates the
minimal pre-launch cross-record invariants needed before a Controller can
safely treat a lane/worktree as claimable.

Implemented invariants:

* two live claims owned by different controllers MUST NOT name the same
  normalized ``worktree_path``;
* released claims, including lapsed releases, do not hold worktree claims;
* stale unreleased claims emit warnings, not hard failures, because
  reclamation/disposition remains an operator-visible lifecycle decision;
* heartbeat ``claim_ref`` and event ``subject_claim_ref`` values MUST resolve
  to a discovered claim record when present;
* live claims MUST be unique per ``(controller_id, lane_id)``;
* heartbeat sequences MUST be monotonically non-decreasing for a claim when
  parseable heartbeat timestamps establish an order;
* event ids MUST be unique within ``(controller_id, lane_id, YYYY-MM-DD)``;
* orphaned atomic-write ``*.tmp.*`` files remain skipped by shared discovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .active_work_ledger_schema import (
    CONTRACT,
    iter_active_work_ledger_records,
    validate_active_work_ledger_record,
)

CHECK_NAME = "active_work_ledger_conflicts"
CODE_WORKTREE_CONFLICT = "PCO-010"
CODE_STALE_WARNING = "PCO-007"
CODE_HEARTBEAT_REF = "PCO-014"
CODE_EVENT_REF = "PCO-015"
CODE_LANE_CONFLICT = "PCO-016"
CODE_HEARTBEAT_MONOTONIC = "PCO-017"
CODE_EVENT_ID_CONFLICT = "PCO-018"


@dataclass(frozen=True)
class LedgerRecord:
    path: Path
    record: dict[str, Any]


def _scan_roots(paths: Iterable[Path]) -> list[Path]:
    roots: list[Path] = []
    for raw in paths:
        path = Path(raw)
        root = path if path.is_dir() else path.parent
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved not in roots:
            roots.append(resolved)
    return roots


def _load_valid_ledger_records(paths: Iterable[Path]) -> list[LedgerRecord]:
    records: list[LedgerRecord] = []
    for record_path in iter_active_work_ledger_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError:
            continue
        if not isinstance(record, dict):
            continue
        if validate_active_work_ledger_record(record, record_path):
            # Schema failures are owned by active_work_ledger_schema.  Avoid
            # cascading cross-record errors from structurally invalid records.
            continue
        records.append(LedgerRecord(path=record_path, record=record))
    return records


def _normalize_worktree_path(value: Any) -> str:
    text = str(value or "").strip()
    while len(text) > 1 and text.endswith("/"):
        text = text[:-1]
    return text


def _claim_key(record: dict[str, Any]) -> tuple[str, str]:
    return (str(record.get("controller_id", "")), str(record.get("lane_id", "")))


def _path_aliases(path: Path, roots: Iterable[Path]) -> set[str]:
    aliases = {path.as_posix()}
    try:
        aliases.add(path.resolve().as_posix())
    except OSError:
        pass
    for root in roots:
        try:
            rel = path.resolve().relative_to(root).as_posix()
        except (OSError, ValueError):
            continue
        aliases.add(rel)
        aliases.add(f".hermes/active-work-ledger/{rel}")
    return aliases


def _build_claim_path_index(records: Iterable[LedgerRecord], roots: Iterable[Path]) -> dict[str, LedgerRecord]:
    index: dict[str, LedgerRecord] = {}
    for item in records:
        if item.record.get("record_type") != "claim":
            continue
        for alias in _path_aliases(item.path, roots):
            index[alias] = item
    return index


def _ref_tail_alias(ref: str) -> str | None:
    parts = Path(ref).parts
    if "claims" not in parts:
        return None
    idx = parts.index("claims")
    return Path(*parts[idx:]).as_posix()


def _resolve_claim_ref(ref: Any, index: dict[str, LedgerRecord]) -> LedgerRecord | None:
    if not isinstance(ref, str) or not ref:
        return None
    if ref in index:
        return index[ref]
    tail = _ref_tail_alias(ref)
    if tail and tail in index:
        return index[tail]
    normalized = ref[2:] if ref.startswith("./") else ref
    if normalized in index:
        return index[normalized]
    return None


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    if value.startswith("commit:") or value.startswith("source-controlled:"):
        return None
    text = value
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _is_released(record: dict[str, Any]) -> bool:
    return "released_at" in record


def _is_stale(record: dict[str, Any], now: datetime) -> bool:
    last_heartbeat_at = _parse_utc(record.get("last_heartbeat_at"))
    lease_seconds = record.get("lease_seconds")
    if last_heartbeat_at is None or not isinstance(lease_seconds, int):
        return False
    return now - last_heartbeat_at > timedelta(seconds=lease_seconds)


def _claim_is_live(record: dict[str, Any], now: datetime) -> bool:
    return not _is_released(record) and not _is_stale(record, now)


def _worktree_conflicts(records: Iterable[LedgerRecord], now: datetime) -> list[ValidationError]:
    errors: list[ValidationError] = []
    live_by_worktree: dict[str, LedgerRecord] = {}
    for item in records:
        record = item.record
        if record.get("record_type") != "claim" or not _claim_is_live(record, now):
            continue
        worktree = _normalize_worktree_path(record.get("worktree_path"))
        if not worktree:
            continue
        existing = live_by_worktree.get(worktree)
        if existing is None:
            live_by_worktree[worktree] = item
            continue
        existing_controller, existing_lane = _claim_key(existing.record)
        controller, lane = _claim_key(record)
        if controller != existing_controller:
            errors.append(
                make_error(
                    CODE_WORKTREE_CONFLICT,
                    item.path,
                    "worktree_path",
                    (
                        f"live claim for worktree {worktree!r} conflicts with "
                        f"{existing.path} ({existing_controller}/{existing_lane})"
                    ),
                    CONTRACT,
                )
            )
    return errors


def _lane_conflicts(records: Iterable[LedgerRecord], now: datetime) -> list[ValidationError]:
    errors: list[ValidationError] = []
    live_by_lane: dict[tuple[str, str], LedgerRecord] = {}
    for item in records:
        record = item.record
        if record.get("record_type") != "claim" or not _claim_is_live(record, now):
            continue
        key = _claim_key(record)
        existing = live_by_lane.get(key)
        if existing is None:
            live_by_lane[key] = item
            continue
        errors.append(
            make_error(
                CODE_LANE_CONFLICT,
                item.path,
                "lane_id",
                f"live claim for controller/lane {key[0]}/{key[1]} conflicts with {existing.path}",
                CONTRACT,
            )
        )
    return errors


def _stale_warnings(records: Iterable[LedgerRecord], now: datetime) -> list[ValidationError]:
    warnings: list[ValidationError] = []
    for item in records:
        record = item.record
        if record.get("record_type") != "claim" or _is_released(record):
            continue
        if _is_stale(record, now):
            warnings.append(
                make_error(
                    CODE_STALE_WARNING,
                    item.path,
                    "last_heartbeat_at",
                    "stale unreleased claim is advisory and requires explicit lifecycle disposition before reuse",
                    CONTRACT,
                )
            )
    return warnings


def _reference_errors(records: Iterable[LedgerRecord], claim_index: dict[str, LedgerRecord]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for item in records:
        record = item.record
        if record.get("record_type") == "heartbeat":
            claim_ref = record.get("claim_ref")
            claim = _resolve_claim_ref(claim_ref, claim_index)
            if claim is None:
                errors.append(
                    make_error(
                        CODE_HEARTBEAT_REF,
                        item.path,
                        "claim_ref",
                        f"heartbeat claim_ref {claim_ref!r} does not resolve to a discovered claim record",
                        CONTRACT,
                    )
                )
                continue
            if _claim_key(record) != _claim_key(claim.record):
                errors.append(
                    make_error(
                        CODE_HEARTBEAT_REF,
                        item.path,
                        "claim_ref",
                        "heartbeat controller_id/lane_id does not match referenced claim",
                        CONTRACT,
                    )
                )
        if record.get("record_type") == "event" and record.get("subject_claim_ref"):
            subject_ref = record.get("subject_claim_ref")
            if _resolve_claim_ref(subject_ref, claim_index) is None:
                errors.append(
                    make_error(
                        CODE_EVENT_REF,
                        item.path,
                        "subject_claim_ref",
                        f"event subject_claim_ref {subject_ref!r} does not resolve to a discovered claim record",
                        CONTRACT,
                    )
                )
    return errors


def _heartbeat_monotonic_errors(
    records: Iterable[LedgerRecord], claim_index: dict[str, LedgerRecord]
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    by_claim: dict[Path, list[tuple[datetime, int, LedgerRecord]]] = {}
    for item in records:
        record = item.record
        if record.get("record_type") != "heartbeat":
            continue
        claim = _resolve_claim_ref(record.get("claim_ref"), claim_index)
        emitted_at = _parse_utc(record.get("emitted_at"))
        sequence = record.get("heartbeat_sequence")
        if claim is None or emitted_at is None or not isinstance(sequence, int):
            continue
        by_claim.setdefault(claim.path, []).append((emitted_at, sequence, item))

    for claim_path, heartbeats in by_claim.items():
        previous_sequence: int | None = None
        previous_item: LedgerRecord | None = None
        for _emitted_at, sequence, item in sorted(
            heartbeats, key=lambda entry: (entry[0], entry[2].path.as_posix())
        ):
            if previous_sequence is not None and sequence < previous_sequence:
                errors.append(
                    make_error(
                        CODE_HEARTBEAT_MONOTONIC,
                        item.path,
                        "heartbeat_sequence",
                        (
                            f"heartbeat sequence {sequence} for claim {claim_path} is lower than "
                            f"previous sequence {previous_sequence} at "
                            f"{previous_item.path if previous_item else 'unknown'}"
                        ),
                        CONTRACT,
                    )
                )
            previous_sequence = sequence
            previous_item = item
    return errors


def _event_day(record: dict[str, Any]) -> str | None:
    event_timestamp = record.get("event_timestamp")
    parsed = _parse_utc(event_timestamp)
    if parsed is not None:
        return parsed.date().isoformat()
    if isinstance(event_timestamp, str) and event_timestamp.startswith("source-controlled:"):
        return event_timestamp
    return None


def _event_id_conflicts(records: Iterable[LedgerRecord]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    seen: dict[tuple[str, str, str, str], LedgerRecord] = {}
    for item in records:
        record = item.record
        if record.get("record_type") != "event":
            continue
        day = _event_day(record)
        event_id = record.get("event_id")
        if day is None or not isinstance(event_id, str):
            continue
        controller_id, lane_id = _claim_key(record)
        key = (controller_id, lane_id, day, event_id)
        existing = seen.get(key)
        if existing is None:
            seen[key] = item
            continue
        errors.append(
            make_error(
                CODE_EVENT_ID_CONFLICT,
                item.path,
                "event_id",
                (
                    f"event_id {event_id!r} is duplicated for controller/lane/day "
                    f"{controller_id}/{lane_id}/{day}; first seen at {existing.path}"
                ),
                CONTRACT,
            )
        )
    return errors


def validate_active_work_ledger_conflicts(
    paths: Iterable[Path], *, now: datetime | None = None
) -> CheckResult:
    scan_paths = [Path(p) for p in paths]
    effective_now = now or datetime.now(UTC)
    records = _load_valid_ledger_records(scan_paths)
    roots = _scan_roots(scan_paths)
    claim_index = _build_claim_path_index(records, roots)
    errors = [
        *_worktree_conflicts(records, effective_now),
        *_lane_conflicts(records, effective_now),
        *_reference_errors(records, claim_index),
        *_heartbeat_monotonic_errors(records, claim_index),
        *_event_id_conflicts(records),
    ]
    warnings = _stale_warnings(records, effective_now)
    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(warnings))


@register(
    CHECK_NAME,
    [
        CODE_WORKTREE_CONFLICT,
        CODE_HEARTBEAT_REF,
        CODE_EVENT_REF,
        CODE_LANE_CONFLICT,
        CODE_HEARTBEAT_MONOTONIC,
        CODE_EVENT_ID_CONFLICT,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    return validate_active_work_ledger_conflicts(paths)
