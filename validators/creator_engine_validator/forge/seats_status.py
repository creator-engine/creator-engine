"""Fleet seat liveness read-model for ``ce seats ls``.

The reader consumes CE-owned state files only:

* ``<state_root>/dispatches/<seat_id>/events.jsonl`` seat sentinel streams
* ``<ledger_root>/seats/<host>/<seat_id>.yaml`` lifecycle registry records

It never inspects terminal panes or subprocess output. The functions below are
kept pure around explicit paths so tests can exercise discovery, state reading,
classification, and rendering without a live CE runtime.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

DISPATCHES_SUBDIR = "dispatches"
EVENTS_FILENAME = "events.jsonl"
ACTIVE_WORK_LEDGER_SUBDIR = "active-work-ledger"
SEATS_SUBDIR = "seats"

STATE_UP = "up"
STATE_IDLE = "idle"
STATE_WORKING = "working"
STATE_DOWN = "down"
STATE_UNKNOWN = "unknown"

_MISSING = "-"


@dataclass(frozen=True)
class SeatRef:
    """A discovered seat state surface."""

    seat_id: str
    host_id: str | None = None
    lifecycle_path: Path | None = None
    events_path: Path | None = None


@dataclass(frozen=True)
class SeatStatus:
    """Rendered seat liveness facts derived from CE state files."""

    seat_id: str
    state: str
    branch: str | None = None
    lane: str | None = None
    host_id: str | None = None
    source: str = "missing-state"
    reason: str = "missing-state"
    lifecycle_path: str | None = None
    events_path: str | None = None


def default_ledger_roots(state_root: Path | str) -> list[Path]:
    """Return ledger roots implied by a state root."""

    root = Path(state_root)
    roots: list[Path] = []
    if (root / SEATS_SUBDIR).is_dir():
        roots.append(root)
    roots.append(root / ACTIVE_WORK_LEDGER_SUBDIR)
    return _dedupe_paths(roots)


def discover_seats(
    state_root: Path | str,
    *,
    ledger_roots: Sequence[Path | str] | None = None,
) -> list[SeatRef]:
    """Discover seat identities from lifecycle records and sentinel dirs."""

    root = Path(state_root)
    refs: dict[str, SeatRef] = {}
    events_seen: set[Path] = set()
    for ledger_root in ledger_roots or default_ledger_roots(root):
        for lifecycle_path in _iter_lifecycle_paths(Path(ledger_root)):
            ref = _ref_from_lifecycle_path(lifecycle_path, state_root=root)
            key = _ref_key(ref)
            refs[key] = _merge_ref(refs.get(key), ref)
            if ref.events_path is not None:
                events_seen.add(_norm_path(ref.events_path))

    dispatches = root / DISPATCHES_SUBDIR
    if dispatches.is_dir():
        for seat_dir in sorted(p for p in dispatches.iterdir() if p.is_dir()):
            events_path = seat_dir / EVENTS_FILENAME
            if _norm_path(events_path) in events_seen:
                continue
            ref = SeatRef(seat_id=seat_dir.name, events_path=events_path)
            key = _ref_key(ref)
            refs[key] = _merge_ref(refs.get(key), ref)

    return sorted(refs.values(), key=lambda r: ((r.host_id or ""), r.seat_id))


def read_seat_states(refs: Iterable[SeatRef]) -> list[SeatStatus]:
    """Read all discovered seats into status records."""

    return [read_seat_state(ref) for ref in refs]


def read_seat_state(ref: SeatRef) -> SeatStatus:
    """Read one seat's durable state and classify its liveness."""

    record, record_reason = _load_mapping(ref.lifecycle_path)
    record_seat = record.get("seat", {}) if record else {}
    record_work = record.get("work", {}) if record else {}
    record_dispatch = record.get("dispatch", {}) if record else {}
    lifecycle = record.get("lifecycle", {}) if record else {}

    seat_id = _first_text(record_seat.get("seat_id"), ref.seat_id)
    host_id = _first_text(record_seat.get("host_id"), ref.host_id)
    events_path = ref.events_path or _events_path_from_ref(
        record_dispatch.get("events_ref"),
        lifecycle_path=ref.lifecycle_path,
    )
    events, events_reason = _load_events(events_path)
    latest_event = events[-1] if events else {}

    branch = _first_text(record_work.get("branch"))
    lane = _first_text(
        record_work.get("ticket"),
        record_dispatch.get("scope_id"),
        record_dispatch.get("run_id"),
        latest_event.get("run_id"),
    )
    source = _source_name(record is not None, bool(events), ref)
    state, reason = _classify(record, latest_event, record_reason, events_reason)

    return SeatStatus(
        seat_id=seat_id or ref.seat_id,
        host_id=host_id,
        state=state,
        branch=branch,
        lane=lane,
        source=source,
        reason=reason,
        lifecycle_path=str(ref.lifecycle_path) if ref.lifecycle_path else None,
        events_path=str(events_path) if events_path else None,
    )


def render_table(statuses: Sequence[SeatStatus]) -> str:
    """Render a stable human table."""

    rows = [
        [
            status.seat_id,
            status.state,
            status.branch or _MISSING,
            status.lane or _MISSING,
            status.source,
        ]
        for status in statuses
    ]
    headers = ["SEAT", "STATE", "BRANCH", "LANE", "SOURCE"]
    if not rows:
        rows = [["(no seats)", _MISSING, _MISSING, _MISSING, _MISSING]]
    widths = [
        max(len(str(row[i])) for row in ([headers] + rows))
        for i in range(len(headers))
    ]
    lines = [_format_row(headers, widths)]
    lines.append(_format_row(["-" * width for width in widths], widths))
    lines.extend(_format_row(row, widths) for row in rows)
    return "\n".join(lines)


def render_json(statuses: Sequence[SeatStatus]) -> str:
    """Render machine-readable status payload."""

    payload = {"seats": [asdict(status) for status in statuses], "count": len(statuses)}
    return json.dumps(payload, indent=2, sort_keys=True)


def add_parser(subparsers: argparse._SubParsersAction, *, default_root: str) -> None:
    """Register the ``seats ls`` CLI surface on an existing parser."""

    seats = subparsers.add_parser("seats", help="list governed seat liveness from CE state")
    seats_sub = seats.add_subparsers(dest="seats_command", required=True)
    ls = seats_sub.add_parser("ls", help="list governed seat liveness")
    ls.add_argument(
        "--root",
        default=default_root,
        help=f"CE local state root containing dispatches/ (default: {default_root})",
    )
    ls.add_argument(
        "--ledger-root",
        action="append",
        default=None,
        dest="ledger_roots",
        help="repeatable lifecycle ledger root containing seats/<host>/*.yaml",
    )
    ls.add_argument("--json", action="store_true", dest="json_output")


def run_cli(args: argparse.Namespace) -> int:
    """CLI adapter for ``seats ls``."""

    if getattr(args, "seats_command", None) != "ls":
        print("ERROR: seats subcommand required", file=sys.stderr)
        return 2
    state_root = Path(args.root)
    ledger_roots = (
        [Path(p) for p in getattr(args, "ledger_roots", None) or []]
        or default_ledger_roots(state_root)
    )
    refs = discover_seats(state_root, ledger_roots=ledger_roots)
    statuses = read_seat_states(refs)
    if getattr(args, "json_output", False):
        print(render_json(statuses))
    else:
        print(render_table(statuses))
    return 0


def _iter_lifecycle_paths(ledger_root: Path) -> list[Path]:
    base = ledger_root / SEATS_SUBDIR
    if not base.is_dir():
        return []
    return sorted(base.glob("*/*.yaml"))


def _ref_from_lifecycle_path(path: Path, *, state_root: Path) -> SeatRef:
    record, _reason = _load_mapping(path)
    seat = record.get("seat", {}) if record else {}
    dispatch = record.get("dispatch", {}) if record else {}
    host_id = _first_text(seat.get("host_id"), path.parent.name)
    seat_id = _first_text(seat.get("seat_id"), path.stem) or path.stem
    return SeatRef(
        seat_id=seat_id,
        host_id=host_id,
        lifecycle_path=path,
        events_path=_events_path_from_ref(
            dispatch.get("events_ref"),
            lifecycle_path=path,
            state_root=state_root,
        ),
    )


def _merge_ref(existing: SeatRef | None, new: SeatRef) -> SeatRef:
    if existing is None:
        return new
    return SeatRef(
        seat_id=existing.seat_id or new.seat_id,
        host_id=existing.host_id or new.host_id,
        lifecycle_path=existing.lifecycle_path or new.lifecycle_path,
        events_path=existing.events_path or new.events_path,
    )


def _ref_key(ref: SeatRef) -> str:
    return f"{ref.host_id or ''}:{ref.seat_id}"


def _load_mapping(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if path is None:
        return None, "missing-lifecycle"
    if not path.is_file():
        return None, "missing-lifecycle"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None, "unreadable-lifecycle"
    if not isinstance(data, dict):
        return None, "malformed-lifecycle"
    return data, None


def _load_events(path: Path | None) -> tuple[list[dict[str, Any]], str | None]:
    if path is None:
        return [], "missing-events"
    if not path.is_file():
        return [], "missing-events"
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [], "unreadable-events"
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events, None if events else "empty-events"


def _classify(
    record: Mapping[str, Any] | None,
    latest_event: Mapping[str, Any],
    record_reason: str | None,
    events_reason: str | None,
) -> tuple[str, str]:
    if latest_event.get("event") == "exited":
        return STATE_DOWN, "sentinel-exited"
    if record:
        lifecycle = record.get("lifecycle", {})
        lifecycle_state = lifecycle.get("state") if isinstance(lifecycle, Mapping) else None
        if lifecycle_state == "idle":
            return STATE_IDLE, "lifecycle-idle"
        if lifecycle_state == "alive":
            if _has_work(record):
                return STATE_WORKING, "lifecycle-alive-with-work"
            return STATE_UP, "lifecycle-alive"
        if lifecycle_state in {"dead", "spent"}:
            return STATE_DOWN, f"lifecycle-{lifecycle_state}"
        return STATE_UNKNOWN, "malformed-lifecycle-state"
    if latest_event.get("event") == "launched":
        return (STATE_WORKING, "sentinel-launched-with-run") if latest_event.get("run_id") else (
            STATE_UP,
            "sentinel-launched",
        )
    return STATE_UNKNOWN, events_reason or record_reason or "missing-state"


def _has_work(record: Mapping[str, Any]) -> bool:
    work = record.get("work", {})
    dispatch = record.get("dispatch", {})
    if isinstance(work, Mapping):
        for key in ("branch", "ticket", "work_claim", "pco_claim_ref", "pco_lease_ref"):
            if work.get(key):
                return True
    if isinstance(dispatch, Mapping):
        for key in ("run_id", "scope_id", "mutation_class"):
            if dispatch.get(key):
                return True
    return False


def _source_name(has_record: bool, has_events: bool, ref: SeatRef) -> str:
    if has_record and has_events:
        return "lifecycle+sentinel"
    if has_record:
        return "lifecycle"
    if has_events:
        return "sentinel"
    if ref.lifecycle_path or ref.events_path:
        return "missing-state"
    return "unknown"


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _path_or_none(value: Any) -> Path | None:
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _events_path_from_ref(
    value: Any,
    *,
    lifecycle_path: Path | None,
    state_root: Path | None = None,
) -> Path | None:
    path = _path_or_none(value)
    if path is None or path.is_absolute():
        return path
    if state_root is not None and path.parts[:1] == (DISPATCHES_SUBDIR,):
        return state_root / path
    if lifecycle_path is not None:
        ledger_root = _ledger_root_from_lifecycle_path(lifecycle_path)
        if ledger_root is not None and path.parts[:1] == (DISPATCHES_SUBDIR,):
            return ledger_root.parent / path
    return path


def _ledger_root_from_lifecycle_path(path: Path) -> Path | None:
    # <ledger_root>/seats/<host_id>/<seat_id>.yaml
    if len(path.parents) >= 3 and path.parents[1].name == SEATS_SUBDIR:
        return path.parents[2]
    return None


def _dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        out.append(path)
    return out


def _norm_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _format_row(row: Sequence[str], widths: Sequence[int]) -> str:
    return "  ".join(str(value).ljust(width) for value, width in zip(row, widths, strict=True))
