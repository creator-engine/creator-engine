"""Fleet containment status probe for CE seats.

The fleet surface intentionally reuses :mod:`containment_probe` for the
containment verdict. Registry files are used only to resolve seat -> pid and
to derive non-containment posture fields such as Herdr/Ring1 presence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from . import containment_probe
from .loader import LoaderError, load_yaml

LIVE_PANE_STATUSES = {"active", "blocked", "closing", "starting"}
HERDR_LIVE = "live"
HERDR_NONE = "none"
RING1_ENFORCED = "enforced"
RING1_NONE = "none"


@dataclass(frozen=True)
class SeatTarget:
    seat: str
    pid: str | None = None
    terminal_kind: str | None = None
    harness: str | None = None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class HarnessMatrix:
    ring1_by_seat: dict[str, bool]
    ring1_by_harness: dict[str, bool]


@dataclass(frozen=True)
class ContainmentStatusRow:
    seat: str
    contained: bool
    backend: str
    herdr_session: str
    ring1: str

    @property
    def payload(self) -> dict[str, Any]:
        return {
            "seat": self.seat,
            "contained": self.contained,
            "backend": self.backend,
            "herdr_session": self.herdr_session,
            "ring1": self.ring1,
        }


@dataclass(frozen=True)
class FleetStatus:
    rows: tuple[ContainmentStatusRow, ...]

    @property
    def ok(self) -> bool:
        return bool(self.rows) and all(row.contained for row in self.rows)

    @property
    def payload(self) -> dict[str, Any]:
        return {"seats": [row.payload for row in self.rows]}


def probe_fleet(
    *,
    seat_specs: Iterable[str],
    registry_paths: Iterable[str | Path],
    proc_root: str | Path = "/proc",
    host_pid: str = "1",
) -> FleetStatus:
    direct_specs, requested_names = _parse_seat_specs(seat_specs)
    records = _load_registry_records(registry_paths)
    matrix = _derive_harness_matrix(records)
    registry_targets = _derive_registry_targets(records)

    rows: list[ContainmentStatusRow] = []
    emitted: set[str] = set()

    for target in direct_specs:
        rows.append(_probe_target(target, matrix=matrix, proc_root=proc_root, host_pid=host_pid))
        emitted.add(target.seat)

    if requested_names:
        for name in requested_names:
            if name in emitted:
                continue
            target = _match_registry_target(name, registry_targets)
            if target is None:
                target = SeatTarget(seat=name)
            rows.append(_probe_target(target, matrix=matrix, proc_root=proc_root, host_pid=host_pid))
            emitted.add(name)
    elif registry_targets:
        for target in registry_targets:
            if target.seat in emitted:
                continue
            rows.append(_probe_target(target, matrix=matrix, proc_root=proc_root, host_pid=host_pid))
            emitted.add(target.seat)

    return FleetStatus(rows=tuple(rows))


def render_table(status: FleetStatus) -> str:
    headers = ("seat", "contained", "backend", "herdr_session", "ring1")
    body = [
        (
            row.seat,
            str(row.contained).lower(),
            row.backend,
            row.herdr_session,
            row.ring1,
        )
        for row in status.rows
    ]
    widths = [
        max(len(headers[idx]), *(len(item[idx]) for item in body)) if body else len(headers[idx])
        for idx in range(len(headers))
    ]
    lines = [
        "  ".join(headers[idx].ljust(widths[idx]) for idx in range(len(headers))),
        "  ".join("-" * widths[idx] for idx in range(len(headers))),
    ]
    for item in body:
        lines.append("  ".join(item[idx].ljust(widths[idx]) for idx in range(len(headers))))
    return "\n".join(lines)


def render_json(status: FleetStatus) -> str:
    return json.dumps(status.payload, indent=2, sort_keys=True)


def _parse_seat_specs(seat_specs: Iterable[str]) -> tuple[list[SeatTarget], list[str]]:
    direct: list[SeatTarget] = []
    names: list[str] = []
    seen_names: set[str] = set()
    for raw in seat_specs:
        for part in str(raw).split(","):
            spec = part.strip()
            if not spec:
                continue
            if "=" in spec:
                seat, pid = (piece.strip() for piece in spec.split("=", 1))
                if not seat or seat in seen_names:
                    continue
                direct.append(SeatTarget(seat=seat, pid=_normalize_pid(pid)))
                seen_names.add(seat)
            elif spec not in seen_names:
                names.append(spec)
                seen_names.add(spec)
    return direct, names


def _load_registry_records(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw in paths:
        root = Path(raw)
        for path in _iter_registry_files(root):
            loaded = _load_registry_file(path)
            records.extend(_expand_loaded_records(loaded))
    return records


def _iter_registry_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        return []
    suffixes = {".yml", ".yaml", ".json"}
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def _load_registry_file(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    try:
        return load_yaml(path)
    except LoaderError:
        return None


def _expand_loaded_records(loaded: Any) -> list[dict[str, Any]]:
    if isinstance(loaded, list):
        return [item for item in loaded if isinstance(item, dict)]
    if not isinstance(loaded, dict):
        return []
    seats = loaded.get("seats")
    if isinstance(seats, list):
        return [item for item in seats if isinstance(item, dict)]
    return [loaded]


def _derive_harness_matrix(records: Iterable[dict[str, Any]]) -> HarnessMatrix:
    by_seat: dict[str, bool] = {}
    by_harness: dict[str, bool] = {}
    for record in records:
        contract = record.get("seat_contract")
        if not isinstance(contract, dict):
            continue
        ring1 = _contract_requires_ring1(contract)
        seat = _string_or_none(contract.get("seat_id"))
        harness = _string_or_none(contract.get("harness"))
        if seat:
            by_seat[seat] = ring1
        if harness:
            by_harness[harness] = ring1
    return HarnessMatrix(ring1_by_seat=by_seat, ring1_by_harness=by_harness)


def _contract_requires_ring1(contract: dict[str, Any]) -> bool:
    hook_pack = contract.get("required_hook_pack")
    return isinstance(hook_pack, dict) and str(hook_pack.get("ring") or "").strip() == "ring_1"


def _derive_registry_targets(records: Iterable[dict[str, Any]]) -> tuple[SeatTarget, ...]:
    targets: list[SeatTarget] = []
    for record in records:
        target = _target_from_record(record)
        if target is not None:
            targets.append(target)
    return tuple(targets)


def _target_from_record(record: dict[str, Any]) -> SeatTarget | None:
    if record.get("kind") == "seat-lifecycle-record":
        return _target_from_lifecycle(record)
    if record.get("kind") == "pane-registry-record":
        return _target_from_pane(record)
    return _target_from_generic(record)


def _target_from_lifecycle(record: dict[str, Any]) -> SeatTarget | None:
    seat = record.get("seat")
    if not isinstance(seat, dict):
        return None
    seat_id = _string_or_none(seat.get("seat_id"))
    if not seat_id:
        return None
    terminal = record.get("terminal") if isinstance(record.get("terminal"), dict) else {}
    harness = record.get("harness") if isinstance(record.get("harness"), dict) else {}
    return SeatTarget(
        seat=seat_id,
        pid=_terminal_pid(terminal),
        terminal_kind=_string_or_none(terminal.get("kind")),
        harness=_string_or_none(harness.get("kind")),
        aliases=_aliases(
            seat_id,
            seat.get("host_id"),
            seat.get("owner_controller_id"),
            terminal.get("pane_id"),
            terminal.get("surface_ref"),
        ),
    )


def _target_from_pane(record: dict[str, Any]) -> SeatTarget | None:
    if record.get("status") not in LIVE_PANE_STATUSES:
        return None
    terminal = record.get("terminal") if isinstance(record.get("terminal"), dict) else {}
    seat = (
        _string_or_none(record.get("seat_id"))
        or _string_or_none(record.get("pane_id"))
        or _string_or_none(record.get("lane_id"))
    )
    if not seat:
        return None
    return SeatTarget(
        seat=seat,
        pid=_terminal_pid(terminal),
        terminal_kind=_string_or_none(terminal.get("kind")),
        harness=_harness_kind(record.get("harness")),
        aliases=_aliases(
            seat,
            record.get("controller_id"),
            record.get("lane_id"),
            record.get("host_id"),
            record.get("pane_id"),
            terminal.get("pane_id"),
            terminal.get("session_id"),
            terminal.get("surface_ref"),
        ),
    )


def _target_from_generic(record: dict[str, Any]) -> SeatTarget | None:
    seat = (
        _string_or_none(record.get("seat"))
        or _string_or_none(record.get("seat_id"))
        or _string_or_none(record.get("id"))
        or _string_or_none(record.get("name"))
    )
    if not seat:
        return None
    terminal = record.get("terminal") if isinstance(record.get("terminal"), dict) else {}
    return SeatTarget(
        seat=seat,
        pid=_normalize_pid(record.get("pid")) or _terminal_pid(terminal),
        terminal_kind=_string_or_none(terminal.get("kind")),
        harness=_harness_kind(record.get("harness")),
        aliases=_aliases(seat, record.get("host_id"), record.get("controller_id"), record.get("lane_id")),
    )


def _match_registry_target(name: str, targets: Iterable[SeatTarget]) -> SeatTarget | None:
    for target in targets:
        if name == target.seat or name in target.aliases:
            return target
    return None


def _probe_target(
    target: SeatTarget,
    *,
    matrix: HarnessMatrix,
    proc_root: str | Path,
    host_pid: str,
) -> ContainmentStatusRow:
    if target.pid:
        reader = containment_probe.ProcReader(root=str(proc_root))
        verdict = containment_probe.probe_containment(target.pid, reader=reader, host_pid=host_pid)
        contained = verdict.contained
        backend = verdict.backend
    else:
        contained = False
        backend = "none"
    return ContainmentStatusRow(
        seat=target.seat,
        contained=contained,
        backend=backend,
        herdr_session=_herdr_session(target, proc_root),
        ring1=_ring1_status(target, matrix),
    )


def _herdr_session(target: SeatTarget, proc_root: str | Path) -> str:
    if target.terminal_kind != "herdr" or not target.pid:
        return HERDR_NONE
    return HERDR_LIVE if _pid_exists(proc_root, target.pid) else HERDR_NONE


def _pid_exists(proc_root: str | Path, pid: str) -> bool:
    try:
        return (Path(proc_root) / str(pid)).exists()
    except OSError:
        return False


def _ring1_status(target: SeatTarget, matrix: HarnessMatrix) -> str:
    if matrix.ring1_by_seat.get(target.seat) is True:
        return RING1_ENFORCED
    if target.harness and matrix.ring1_by_harness.get(target.harness) is True:
        return RING1_ENFORCED
    return RING1_NONE


def _terminal_pid(terminal: dict[str, Any]) -> str | None:
    return _normalize_pid(terminal.get("pid")) or _normalize_pid(terminal.get("pane_pid"))


def _harness_kind(value: Any) -> str | None:
    if isinstance(value, dict):
        return _string_or_none(value.get("kind"))
    return _string_or_none(value)


def _normalize_pid(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.isdigit() and int(text) > 0:
        return text
    return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _aliases(*values: Any) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _string_or_none(value)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)
