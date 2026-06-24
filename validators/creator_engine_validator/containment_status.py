"""Fleet containment status probe for CE seats."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from . import containment_probe
from . import harness_matrix
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
    herdr_socket: str | None = None
    herdr_pane_id: str | None = None
    aliases: tuple[str, ...] = ()


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
    repo_root: str | Path = ".",
    proc_root: str | Path = "/proc",
    host_pid: str = "1",
    herdr_socket: str | None = None,
    herdr_binary: str = "herdr",
    ring1_tool: str = "git",
) -> FleetStatus:
    direct_specs, requested_names = _parse_seat_specs(seat_specs)
    records = _load_registry_records(registry_paths)
    matrix_targets = _derive_matrix_targets(repo_root)
    registry_targets = _derive_registry_targets(records, matrix_targets=matrix_targets)

    rows: list[ContainmentStatusRow] = []
    emitted: set[str] = set()

    for target in direct_specs:
        rows.append(
            _probe_target(
                _with_default_herdr_socket(target, herdr_socket),
                proc_root=proc_root,
                host_pid=host_pid,
                herdr_binary=herdr_binary,
                ring1_tool=ring1_tool,
            )
        )
        emitted.add(target.seat)

    if requested_names:
        for name in requested_names:
            if name in emitted:
                continue
            target = _match_registry_target(name, registry_targets)
            if target is None:
                target = SeatTarget(seat=name)
            rows.append(
                _probe_target(
                    _with_default_herdr_socket(target, herdr_socket),
                    proc_root=proc_root,
                    host_pid=host_pid,
                    herdr_binary=herdr_binary,
                    ring1_tool=ring1_tool,
                )
            )
            emitted.add(name)
    elif not direct_specs:
        for target in _bind_registry_targets(matrix_targets, registry_targets):
            if target.seat in emitted:
                continue
            rows.append(
                _probe_target(
                    _with_default_herdr_socket(target, herdr_socket),
                    proc_root=proc_root,
                    host_pid=host_pid,
                    herdr_binary=herdr_binary,
                    ring1_tool=ring1_tool,
                )
            )
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


def _derive_matrix_targets(repo_root: str | Path) -> tuple[SeatTarget, ...]:
    matrix = harness_matrix.build_matrix(repo_root=repo_root)
    return tuple(SeatTarget(seat=row.harness) for row in matrix.rows)


def _derive_registry_targets(
    records: Iterable[dict[str, Any]],
    *,
    matrix_targets: Iterable[SeatTarget],
) -> tuple[SeatTarget, ...]:
    records_tuple = tuple(records)
    matrix_harnesses = {target.seat for target in matrix_targets}
    seat_contract_harnesses = _seat_contract_harnesses(records_tuple, matrix_harnesses)
    targets: list[SeatTarget] = []
    for record in records_tuple:
        target = _target_from_record(
            record,
            matrix_harnesses=matrix_harnesses,
            seat_contract_harnesses=seat_contract_harnesses,
        )
        if target is not None:
            targets.append(target)
    return tuple(targets)


def _bind_registry_targets(
    matrix_targets: Iterable[SeatTarget],
    registry_targets: Iterable[SeatTarget],
) -> tuple[SeatTarget, ...]:
    by_seat = {target.seat: target for target in registry_targets}
    return tuple(by_seat.get(target.seat, target) for target in matrix_targets)


def _seat_contract_harnesses(
    records: Iterable[dict[str, Any]],
    matrix_harnesses: set[str],
) -> dict[str, str]:
    seat_harnesses: dict[str, str] = {}
    for record in records:
        contract = record.get("seat_contract")
        if not isinstance(contract, dict):
            continue
        seat_id = _string_or_none(contract.get("seat_id"))
        harness = _string_or_none(contract.get("harness"))
        if seat_id and harness in matrix_harnesses:
            seat_harnesses[seat_id] = harness
    return seat_harnesses


def _target_from_record(
    record: dict[str, Any],
    *,
    matrix_harnesses: set[str],
    seat_contract_harnesses: dict[str, str],
) -> SeatTarget | None:
    if record.get("kind") == "seat-lifecycle-record":
        return _target_from_lifecycle(
            record,
            matrix_harnesses=matrix_harnesses,
            seat_contract_harnesses=seat_contract_harnesses,
        )
    if record.get("kind") == "pane-registry-record":
        return _target_from_pane(
            record,
            matrix_harnesses=matrix_harnesses,
            seat_contract_harnesses=seat_contract_harnesses,
        )
    return _target_from_generic(record, matrix_harnesses=matrix_harnesses)


def _target_from_lifecycle(
    record: dict[str, Any],
    *,
    matrix_harnesses: set[str],
    seat_contract_harnesses: dict[str, str],
) -> SeatTarget | None:
    seat = record.get("seat")
    if not isinstance(seat, dict):
        return None
    seat_id = _string_or_none(seat.get("seat_id"))
    if not seat_id:
        return None
    harness = _record_harness(
        record,
        seat_id=seat_id,
        matrix_harnesses=matrix_harnesses,
        seat_contract_harnesses=seat_contract_harnesses,
    )
    if not harness:
        return None
    terminal = record.get("terminal") if isinstance(record.get("terminal"), dict) else {}
    return SeatTarget(
        seat=harness,
        pid=_terminal_pid(terminal),
        terminal_kind=_string_or_none(terminal.get("kind")),
        herdr_socket=_herdr_socket(record, terminal),
        herdr_pane_id=_string_or_none(terminal.get("pane_id")),
        aliases=_target_aliases(seat_id, harness),
    )


def _target_from_pane(
    record: dict[str, Any],
    *,
    matrix_harnesses: set[str],
    seat_contract_harnesses: dict[str, str],
) -> SeatTarget | None:
    if record.get("status") not in LIVE_PANE_STATUSES:
        return None
    terminal = record.get("terminal") if isinstance(record.get("terminal"), dict) else {}
    seat_id = (
        _string_or_none(record.get("seat_id"))
        or _string_or_none(record.get("pane_id"))
        or _string_or_none(record.get("lane_id"))
    )
    if not seat_id:
        return None
    harness = _record_harness(
        record,
        seat_id=seat_id,
        matrix_harnesses=matrix_harnesses,
        seat_contract_harnesses=seat_contract_harnesses,
    )
    if not harness:
        return None
    return SeatTarget(
        seat=harness,
        pid=_terminal_pid(terminal),
        terminal_kind=_string_or_none(terminal.get("kind")),
        herdr_socket=_herdr_socket(record, terminal),
        herdr_pane_id=_string_or_none(terminal.get("pane_id")),
        aliases=_target_aliases(seat_id, harness),
    )


def _target_from_generic(
    record: dict[str, Any],
    *,
    matrix_harnesses: set[str],
) -> SeatTarget | None:
    seat = (
        _string_or_none(record.get("seat"))
        or _string_or_none(record.get("seat_id"))
        or _string_or_none(record.get("id"))
        or _string_or_none(record.get("name"))
    )
    if not seat or seat not in matrix_harnesses:
        return None
    terminal = record.get("terminal") if isinstance(record.get("terminal"), dict) else {}
    return SeatTarget(
        seat=seat,
        pid=_normalize_pid(record.get("pid")) or _terminal_pid(terminal),
        terminal_kind=_string_or_none(terminal.get("kind")),
        herdr_socket=_herdr_socket(record, terminal),
        herdr_pane_id=_string_or_none(terminal.get("pane_id")),
    )


def _record_harness(
    record: dict[str, Any],
    *,
    seat_id: str,
    matrix_harnesses: set[str],
    seat_contract_harnesses: dict[str, str],
) -> str | None:
    mapped = seat_contract_harnesses.get(seat_id)
    if mapped in matrix_harnesses:
        return mapped
    candidates: list[str | None] = []
    harness = record.get("harness")
    if isinstance(harness, dict):
        candidates.append(_string_or_none(harness.get("kind")))
        candidates.append(_string_or_none(harness.get("harness")))
    else:
        candidates.append(_string_or_none(harness))
    candidates.append(_string_or_none(record.get("harness_kind")))
    candidates.append(seat_id if seat_id in matrix_harnesses else None)
    for candidate in candidates:
        if candidate in matrix_harnesses:
            return candidate
    return None


def _target_aliases(seat_id: str, harness: str) -> tuple[str, ...]:
    return (seat_id,) if seat_id != harness else ()


def _match_registry_target(name: str, targets: Iterable[SeatTarget]) -> SeatTarget | None:
    for target in targets:
        if name == target.seat or name in target.aliases:
            return target
    return None


def _probe_target(
    target: SeatTarget,
    *,
    proc_root: str | Path,
    host_pid: str,
    herdr_binary: str,
    ring1_tool: str,
) -> ContainmentStatusRow:
    reader = containment_probe.ProcReader(root=str(proc_root))
    if target.pid:
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
        herdr_session=_herdr_session(target, herdr_binary=herdr_binary),
        ring1=_ring1_status(target, reader=reader, tool=ring1_tool),
    )


def _with_default_herdr_socket(target: SeatTarget, socket_path: str | None) -> SeatTarget:
    if target.herdr_socket or not socket_path:
        return target
    return SeatTarget(
        seat=target.seat,
        pid=target.pid,
        terminal_kind=target.terminal_kind,
        herdr_socket=socket_path,
        herdr_pane_id=target.herdr_pane_id,
        aliases=target.aliases,
    )


def _herdr_session(target: SeatTarget, *, herdr_binary: str) -> str:
    if target.terminal_kind != "herdr":
        return HERDR_NONE
    verdict = containment_probe.probe_herdr_session(
        socket_path=target.herdr_socket,
        pane_id=target.herdr_pane_id,
        herdr_binary=herdr_binary,
    )
    return HERDR_LIVE if verdict.get("live") is True else HERDR_NONE


def _ring1_status(target: SeatTarget, *, reader: containment_probe.ProcReader, tool: str) -> str:
    if not target.pid:
        return RING1_NONE
    verdict = containment_probe.probe_ring1_enforcement(target.pid, reader=reader, tool=tool)
    if verdict.get("enforced") is True:
        return RING1_ENFORCED
    return RING1_NONE


def _herdr_socket(record: dict[str, Any], terminal: dict[str, Any]) -> str | None:
    return (
        _string_or_none(terminal.get("herdr_socket"))
        or _string_or_none(terminal.get("socket_path"))
        or _string_or_none(terminal.get("control_socket_path"))
        or _string_or_none(record.get("herdr_socket"))
        or _string_or_none(record.get("socket_path"))
        or _string_or_none(record.get("control_socket_path"))
    )


def _terminal_pid(terminal: dict[str, Any]) -> str | None:
    return _normalize_pid(terminal.get("pid")) or _normalize_pid(terminal.get("pane_pid"))


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
