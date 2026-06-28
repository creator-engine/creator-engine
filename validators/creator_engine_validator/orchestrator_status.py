"""Read-only Orchestrator runtime status projection."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from .orchestrator_records import validate_orchestrator_record


@dataclass(frozen=True)
class RecordGroup:
    key: str
    dirname: str
    kind: str
    id_field: str


RECORD_GROUPS: tuple[RecordGroup, ...] = (
    RecordGroup("checkpoints", "checkpoints", "ce-orchestrator-checkpoint", "checkpoint_id"),
    RecordGroup("territory_maps", "territory-maps", "ce-orchestrator-territory-map", "map_id"),
    RecordGroup("harvest_packets", "harvest-packets", "ce-orchestrator-harvest-packet", "packet_id"),
    RecordGroup(
        "operator_decisions",
        "operator-decisions",
        "ce-orchestrator-operator-decision",
        "decision_id",
    ),
)


def default_state_dir(repo_root: str | Path = ".") -> Path:
    return Path(repo_root) / ".ce" / "state" / "orchestrator"


def load_status(repo_root: str | Path = ".", state_dir: str | Path | None = None) -> dict[str, Any]:
    """Load, validate, and summarize Orchestrator runtime records.

    Missing state directories and empty record directories are valid empty
    states. Malformed JSON or schema-invalid records are returned in ``errors``
    without raising so callers can render an actionable cockpit view.
    """

    root = Path(state_dir) if state_dir is not None else default_state_dir(repo_root)
    records: dict[str, list[dict[str, Any]]] = {group.key: [] for group in RECORD_GROUPS}
    errors: list[dict[str, str]] = []

    for group in RECORD_GROUPS:
        directory = root / group.dirname
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(_error(path, group.kind, exc))
                continue
            try:
                validate_orchestrator_record(group.kind, record)
            except (JsonSchemaValidationError, ValueError) as exc:
                errors.append(_error(path, group.kind, exc))
                continue
            records[group.key].append(_summarize_record(group, path, record))

    counts = {key: len(value) for key, value in records.items()}
    total = sum(counts.values())
    latest = {
        key: _latest_record(value)
        for key, value in records.items()
    }
    pending_decisions = [
        record
        for record in records["operator_decisions"]
        if record.get("resolution_status") == "pending"
    ]

    return {
        "ok": not errors,
        "state_dir": str(root),
        "record_count": total,
        "counts": counts,
        "latest": latest,
        "pending_operator_decisions": pending_decisions,
        "records": records,
        "errors": errors,
    }


def render_human(status: dict[str, Any]) -> str:
    state = "OK" if status.get("ok") else "INVALID"
    lines = [
        f"ce orchestrator status: {state} ({status.get('record_count', 0)} record(s))",
        f"state_dir: {status.get('state_dir')}",
    ]

    counts = status.get("counts", {})
    lines.append(
        "records: "
        + ", ".join(
            f"{label}={counts.get(key, 0)}"
            for key, label in (
                ("checkpoints", "checkpoints"),
                ("territory_maps", "territory_maps"),
                ("harvest_packets", "harvest_packets"),
                ("operator_decisions", "operator_decisions"),
            )
        )
    )

    if status.get("record_count", 0) == 0:
        lines.append("no orchestrator runtime records found")
    else:
        latest = status.get("latest", {})
        checkpoint = latest.get("checkpoints")
        if checkpoint:
            gate = checkpoint.get("gate") or {}
            lines.append(
                "latest checkpoint: "
                f"{checkpoint.get('id')} state={checkpoint.get('lifecycle_state')} "
                f"validation={gate.get('validation', '-')} "
                f"review={gate.get('independent_review', '-')}"
            )
            lines.append(f"next_action: {checkpoint.get('next_action') or '-'}")

        territory_map = latest.get("territory_maps")
        if territory_map:
            lines.append(
                "latest territory map: "
                f"{territory_map.get('id')} entries={territory_map.get('entry_count', 0)} "
                f"collisions={_format_counts(territory_map.get('collision_results', {}))}"
            )

        harvest_packet = latest.get("harvest_packets")
        if harvest_packet:
            lines.append(
                "latest harvest packet: "
                f"{harvest_packet.get('id')} worker={harvest_packet.get('worker_id')} "
                f"validation={harvest_packet.get('validation_result')} "
                f"stop_line={harvest_packet.get('stop_line_result')}"
            )

        pending = status.get("pending_operator_decisions", [])
        lines.append(f"pending operator decisions: {len(pending)}")
        for decision in pending:
            lines.append(
                "  "
                f"{decision.get('id')}: halt={decision.get('halt_until_resolved')} "
                f"recommended={decision.get('recommended_option')} "
                f"request={decision.get('request')}"
            )

    errors = status.get("errors", [])
    if errors:
        lines.append("validation errors:")
        for error in errors:
            lines.append(f"  {error['path']}: {error['message']}")

    return "\n".join(lines)


def _error(path: Path, kind: str, exc: BaseException) -> dict[str, str]:
    return {
        "path": str(path),
        "kind": kind,
        "message": str(exc),
    }


def _latest_record(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    return sorted(records, key=lambda record: (str(record.get("created_at") or ""), record["path"]))[-1]


def _summarize_record(group: RecordGroup, path: Path, record: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": str(path),
        "kind": group.kind,
        "id": record[group.id_field],
    }
    created_at = record.get("created_at")
    if created_at is not None:
        summary["created_at"] = created_at

    if group.key == "checkpoints":
        gate = dict(record.get("gate", {}))
        summary.update(
            {
                "controller_id": record.get("controller_id"),
                "objective": record.get("objective"),
                "lifecycle_state": record.get("lifecycle_state"),
                "active_claim_count": len(record.get("active_claims", [])),
                "territory_map_ref": record.get("territory_map_ref"),
                "operator_decision_count": len(record.get("operator_decisions", [])),
                "gate": gate,
                "next_action": record.get("next_action"),
            }
        )
    elif group.key == "territory_maps":
        entries = record.get("entries", [])
        collision_checks = record.get("collision_checks", [])
        summary.update(
            {
                "base_ref": record.get("base_ref"),
                "entry_count": len(entries),
                "lock_statuses": dict(Counter(entry.get("lock_status") for entry in entries)),
                "collision_results": dict(Counter(check.get("result") for check in collision_checks)),
            }
        )
    elif group.key == "harvest_packets":
        evidence = record.get("evidence", {})
        summary.update(
            {
                "worker_id": record.get("worker_id"),
                "role": record.get("role"),
                "branch": record.get("branch"),
                "base_ref": record.get("base_ref"),
                "head_sha": record.get("head_sha"),
                "changed_path_count": len(record.get("changed_paths", [])),
                "validation_result": evidence.get("validation_result"),
                "stop_line_result": record.get("stop_line_result"),
                "scope_verdict": record.get("scope_verdict"),
            }
        )
    elif group.key == "operator_decisions":
        resolution = record.get("resolution", {})
        summary.update(
            {
                "requested_by": record.get("requested_by"),
                "authority_basis": record.get("authority_basis"),
                "request": record.get("request"),
                "recommended_option": record.get("recommended_option"),
                "halt_until_resolved": record.get("halt_until_resolved"),
                "resolution_status": resolution.get("status"),
                "resolved_at": resolution.get("resolved_at"),
            }
        )

    return summary


def _format_counts(counts: dict[str, Any]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


__all__ = ["RECORD_GROUPS", "default_state_dir", "load_status", "render_human"]
