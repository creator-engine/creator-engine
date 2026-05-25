"""Active-Work Ledger cross-record conflict validation (PCO Slice 1/2 + 2A).

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

Slice 2A additive predicates (gated on the discovery of at least one
valid ``worktree_lease`` record in the scanned tree, so trees with zero
lease records preserve Slice 1/2 behavior unchanged):

* a live claim's ``worktree_path`` MUST be covered by a live, non-expired
  Worktree Lease record under the **same** ``controller_id`` (``PCO-021``);
* two live leases for the same ``worktree_path`` under *different*
  ``controller_id`` values is itself a conflict (``PCO-022``);
* structurally invalid lease records surfaced during the conflict scan
  emit ``PCO-023`` so the schema-validity surface is not silently widened.
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
from .container_instance import (
    iter_container_instance_records,
    validate_container_instance,
)
from .worker_container_policy import (
    CONTRACT as WORKER_CONTRACT,
    iter_worker_container_policy_records,
    validate_worker_container_policy,
)
from .worktree_lease_schema import (
    CONTRACT as LEASE_CONTRACT,
    iter_worktree_lease_records,
    validate_worktree_lease_record,
)

CHECK_NAME = "active_work_ledger_conflicts"
CODE_WORKTREE_CONFLICT = "PCO-010"
CODE_STALE_WARNING = "PCO-007"
CODE_HEARTBEAT_REF = "PCO-014"
CODE_EVENT_REF = "PCO-015"
CODE_LANE_CONFLICT = "PCO-016"
CODE_HEARTBEAT_MONOTONIC = "PCO-017"
CODE_EVENT_ID_CONFLICT = "PCO-018"
CODE_CLAIM_REQUIRES_LEASE = "PCO-021"
CODE_WORKTREE_LEASE_CONFLICT = "PCO-022"
CODE_LEASE_INVALID_RECORD = "PCO-023"
CODE_CONTAINER_REQUIRED = "PCO-042"

# §g.1: the ratified governance path for worker-container policy records. Only
# PCO-040-valid policies under this path arm the PCO-042 runtime gate; policies
# that live elsewhere (e.g. illustrative examples/ fixtures) do NOT, which keeps
# `check examples/well-formed` green even though it bundles policies and
# unpaired live claims in a single scanned tree.
GOVERNANCE_POLICY_SEGMENTS = ("governance", "policies", "worker-container")


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


@dataclass(frozen=True)
class LeaseRecord:
    path: Path
    record: dict[str, Any]


def _load_lease_records(
    paths: Iterable[Path],
) -> tuple[list[LeaseRecord], list[ValidationError]]:
    """Discover lease records, partitioning valid from invalid.

    Invalid lease records surface as ``PCO-023`` so the conflict scan
    fails loudly when malformed lease state would otherwise silently
    disable the Slice 2A predicates. Schema-valid leases are returned
    for the lease-aware predicates to operate on.
    """
    valid: list[LeaseRecord] = []
    invalid: list[ValidationError] = []
    for record_path in iter_worktree_lease_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            invalid.append(
                make_error(
                    CODE_LEASE_INVALID_RECORD,
                    record_path,
                    "",
                    f"worktree-lease record could not be loaded: {exc}",
                    LEASE_CONTRACT,
                )
            )
            continue
        if not isinstance(record, dict):
            invalid.append(
                make_error(
                    CODE_LEASE_INVALID_RECORD,
                    record_path,
                    "/",
                    "worktree-lease record must be a YAML mapping",
                    LEASE_CONTRACT,
                )
            )
            continue
        if validate_worktree_lease_record(record, record_path):
            invalid.append(
                make_error(
                    CODE_LEASE_INVALID_RECORD,
                    record_path,
                    "/",
                    "worktree-lease record fails schema validation; resolve PCO-020 first",
                    LEASE_CONTRACT,
                )
            )
            continue
        valid.append(LeaseRecord(path=record_path, record=record))
    return valid, invalid


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


def _lease_is_live(record: dict[str, Any], now: datetime) -> bool:
    """A lease is live when ``now < expires_at``.

    Source-controlled or commit-based ``expires_at`` values are not
    resolvable against wall-clock ``now``; they default to live in the
    same spirit that the ledger conflict layer leaves those timestamp
    shapes structurally valid but advisory for time-axis predicates.
    """
    expires_at = record.get("expires_at")
    parsed = _parse_utc(expires_at)
    if parsed is None:
        return True
    return now < parsed


def _lease_key(record: dict[str, Any]) -> tuple[str, str]:
    return (
        str(record.get("controller_id", "")),
        _normalize_worktree_path(record.get("worktree_path")),
    )


def _worktree_lease_conflicts(
    leases: Iterable[LeaseRecord], now: datetime
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    live_by_worktree: dict[str, LeaseRecord] = {}
    for item in leases:
        record = item.record
        if not _lease_is_live(record, now):
            continue
        worktree = _normalize_worktree_path(record.get("worktree_path"))
        if not worktree:
            continue
        existing = live_by_worktree.get(worktree)
        if existing is None:
            live_by_worktree[worktree] = item
            continue
        existing_controller = str(existing.record.get("controller_id", ""))
        controller = str(record.get("controller_id", ""))
        if controller != existing_controller:
            errors.append(
                make_error(
                    CODE_WORKTREE_LEASE_CONFLICT,
                    item.path,
                    "worktree_path",
                    (
                        f"live worktree lease for {worktree!r} conflicts with "
                        f"{existing.path} ({existing_controller})"
                    ),
                    LEASE_CONTRACT,
                )
            )
    return errors


def _claim_requires_live_lease(
    claims: Iterable[LedgerRecord],
    leases: Iterable[LeaseRecord],
    now: datetime,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    live_lease_coverage: set[tuple[str, str]] = {
        _lease_key(lease.record)
        for lease in leases
        if _lease_is_live(lease.record, now)
        and _normalize_worktree_path(lease.record.get("worktree_path"))
    }
    for item in claims:
        record = item.record
        if record.get("record_type") != "claim" or not _claim_is_live(record, now):
            continue
        worktree = _normalize_worktree_path(record.get("worktree_path"))
        if not worktree:
            continue
        controller = str(record.get("controller_id", ""))
        if (controller, worktree) in live_lease_coverage:
            continue
        errors.append(
            make_error(
                CODE_CLAIM_REQUIRES_LEASE,
                item.path,
                "worktree_path",
                (
                    f"live claim for worktree {worktree!r} under controller "
                    f"{controller!r} is not covered by a live worktree-lease "
                    "record under the same controller"
                ),
                LEASE_CONTRACT,
            )
        )
    return errors


def _is_governance_policy_path(path: Path) -> bool:
    """True when ``path`` sits under ``governance/policies/worker-container/``."""
    parts = path.parts
    width = len(GOVERNANCE_POLICY_SEGMENTS)
    return any(
        parts[index : index + width] == GOVERNANCE_POLICY_SEGMENTS
        for index in range(len(parts))
    )


def _governance_policy_present(paths: Iterable[Path]) -> bool:
    """PCO-042 arming gate: a PCO-040-valid policy under the governance path."""
    for policy_path in iter_worker_container_policy_records(paths):
        if not _is_governance_policy_path(policy_path):
            continue
        try:
            record = load_yaml(policy_path)
        except LoaderError:
            continue
        if not isinstance(record, dict):
            continue
        if validate_worker_container_policy(record, policy_path):
            # A malformed governance policy is owned by PCO-040; it does not
            # silently arm (or silently disarm) the PCO-042 runtime gate here.
            continue
        return True
    return False


def _running_instance_claim_ids(paths: Iterable[Path]) -> set[str]:
    """claim_ids of schema-valid container-instance records still running.

    A running instance is one whose ``stopped_at`` is null. The instance's
    ``claim_id`` is the lane_id of the claim it is paired with (claims are keyed
    by ``(controller_id, lane_id)`` and carry no separate ``claim_id`` field).
    """
    running: set[str] = set()
    for instance_path in iter_container_instance_records(paths):
        try:
            record = load_yaml(instance_path)
        except LoaderError:
            continue
        if not isinstance(record, dict):
            continue
        if validate_container_instance(record, instance_path):
            continue
        if record.get("stopped_at") is not None:
            continue
        claim_id = record.get("claim_id")
        if isinstance(claim_id, str) and claim_id:
            running.add(claim_id)
    return running


def _container_required_errors(
    records: Iterable[LedgerRecord], running_claim_ids: set[str]
) -> list[ValidationError]:
    """PCO-042: every live claim must be paired with a running container.

    Applies only when the arming gate (governance policy present) has fired.
    A live claim is one whose ``released_at`` is null; the claim's identity for
    pairing is its ``lane_id``.
    """
    errors: list[ValidationError] = []
    for item in records:
        record = item.record
        if record.get("record_type") != "claim" or _is_released(record):
            continue
        controller_id = str(record.get("controller_id", ""))
        lane_id = str(record.get("lane_id", ""))
        if lane_id in running_claim_ids:
            continue
        errors.append(
            make_error(
                CODE_CONTAINER_REQUIRED,
                item.path,
                "claim_id",
                (
                    "live claim has no paired running container instance "
                    f"(claim_id={lane_id!r}, lane_id={lane_id!r}, "
                    f"controller_id={controller_id!r}); a ratified worker-container "
                    "policy is present, so the lane MUST allocate a worker via "
                    "allocate_worker before launch (PCO-042, §m.1)"
                ),
                WORKER_CONTRACT,
            )
        )
    return errors


def validate_active_work_ledger_conflicts(
    paths: Iterable[Path], *, now: datetime | None = None
) -> CheckResult:
    scan_paths = [Path(p) for p in paths]
    effective_now = now or datetime.now(UTC)
    records = _load_valid_ledger_records(scan_paths)
    leases, lease_errors = _load_lease_records(scan_paths)
    roots = _scan_roots(scan_paths)
    claim_index = _build_claim_path_index(records, roots)
    errors: list[ValidationError] = [
        *_worktree_conflicts(records, effective_now),
        *_lane_conflicts(records, effective_now),
        *_reference_errors(records, claim_index),
        *_heartbeat_monotonic_errors(records, claim_index),
        *_event_id_conflicts(records),
    ]
    # Slice 2A additive predicates are gated on the discovery of at
    # least one valid worktree-lease record in the scanned tree so
    # trees with zero lease records preserve Slice 1/2 behavior.
    if leases:
        errors.extend(_worktree_lease_conflicts(leases, effective_now))
        errors.extend(_claim_requires_live_lease(records, leases, effective_now))
    errors.extend(lease_errors)
    # PCO-042 (Slice 2I-R runtime gate): armed only when a PCO-040-valid
    # worker-container policy is present under the ratified governance path.
    # Trees without such a policy preserve Slice 2R behavior unchanged.
    if _governance_policy_present(scan_paths):
        running_claim_ids = _running_instance_claim_ids(scan_paths)
        errors.extend(_container_required_errors(records, running_claim_ids))
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
        CODE_CLAIM_REQUIRES_LEASE,
        CODE_WORKTREE_LEASE_CONFLICT,
        CODE_LEASE_INVALID_RECORD,
        CODE_CONTAINER_REQUIRED,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    return validate_active_work_ledger_conflicts(paths)
