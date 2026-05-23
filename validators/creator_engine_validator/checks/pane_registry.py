"""Pane Registry substrate validation (PCO Slice 3).

The Pane Registry records operator-visible pane identity and binds live
pane records to Active-Work Ledger claims. This module intentionally
stays in schema/examples/validator territory: no terminal automation,
runtime allocation, provider authority, or MCP/plugin configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register
from .active_work_ledger_schema import iter_active_work_ledger_records, validate_active_work_ledger_record
from .container_instance import iter_container_instance_records, validate_container_instance

CHECK_NAME = "pane_registry"
CONTRACT = "docs/operations/PANE_REGISTRY_PROTOCOL.md"
SCHEMA = "schemas/pane-registry.schema.yaml"
KIND_VALUE = "pane-registry-record"

CODE_SCHEMA = "PCO-046"
CODE_ID_FORMAT = "PCO-047"
CODE_ROLE_STATUS = "PCO-048"
CODE_OPERATOR_VISIBLE = "PCO-049"
CODE_LEDGER_BINDING = "PCO-050"
CODE_DUPLICATE_LIVE_PANE = "PCO-051"
CODE_CONTAINER_BINDING = "PCO-052"
CODE_UNKNOWN_FIELDS = "PCO-053"
CODE_INVALID = "pane_registry_invalid_record"

LIVE_STATUSES = {"active", "blocked", "closing"}
DUPLICATE_REFUSAL_STATUSES = {"active"}
TERMINAL_STATUSES = {"closed", "aborted"}
FORBIDDEN_ID_TOKENS = (
    "account",
    "anthropic",
    "api",
    "claude",
    "credential",
    "gpt",
    "key",
    "model",
    "openai",
    "provider",
    "secret",
    "token",
)


@dataclass(frozen=True)
class RegistryRecord:
    path: Path
    record: dict[str, Any]


@dataclass(frozen=True)
class ClaimRecord:
    path: Path
    record: dict[str, Any]


@dataclass(frozen=True)
class ContainerRecord:
    path: Path
    record: dict[str, Any]


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_pane(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_pane_registry_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Pane Registry files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p)
                and not _is_under_excluded(p)
                and not _is_tmp_artifact(p)
            ]
        else:
            candidates = []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            try:
                data = load_yaml(candidate)
            except LoaderError:
                continue
            if not _record_is_pane(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def _id_surface_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for field in ("host_id", "pane_id"):
        value = record.get(field)
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        for token in FORBIDDEN_ID_TOKENS:
            if token in lowered:
                errors.append(
                    make_error(
                        CODE_ID_FORMAT,
                        path,
                        field,
                        f"{field} must not encode secret, account, model, or provider authority",
                        CONTRACT,
                    )
                )
                break
    return errors


def _role_status_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    status = record.get("status")
    has_closed_at = "closed_at" in record
    has_reason = "close_reason" in record
    if status in TERMINAL_STATUSES and (not has_closed_at or not has_reason):
        errors.append(
            make_error(
                CODE_ROLE_STATUS,
                path,
                "status",
                "terminal status requires closed_at and close_reason",
                CONTRACT,
            )
        )
    if status in LIVE_STATUSES and (has_closed_at or has_reason):
        errors.append(
            make_error(
                CODE_ROLE_STATUS,
                path,
                "status",
                "live status must not carry terminal lifecycle fields",
                CONTRACT,
            )
        )
    return errors


def _operator_visible_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    terminal = record.get("terminal")
    if not isinstance(terminal, dict):
        return []
    if terminal.get("kind") != "tmux":
        return [
            make_error(
                CODE_OPERATOR_VISIBLE,
                path,
                "terminal.kind",
                "operator-visible Pane Registry records require terminal.kind: tmux",
                CONTRACT,
            )
        ]
    missing = [field for field in ("session_id", "window_id", "pane_id") if not terminal.get(field)]
    if missing:
        return [
            make_error(
                CODE_OPERATOR_VISIBLE,
                path,
                "terminal",
                f"tmux terminal identity is missing: {', '.join(missing)}",
                CONTRACT,
            )
        ]
    return []


def validate_pane_registry_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one Pane Registry record against schema and local predicates."""
    errors = validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)
    for error in tuple(errors):
        if "Unevaluated properties" in error.message:
            errors.append(
                make_error(
                    CODE_UNKNOWN_FIELDS,
                    path,
                    "/",
                    "Pane Registry records refuse unknown fields",
                    CONTRACT,
                )
            )
    errors.extend(_id_surface_errors(record, path))
    errors.extend(_role_status_errors(record, path))
    errors.extend(_operator_visible_errors(record, path))
    return errors


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    if value.startswith("commit:") or value.startswith("source-controlled:"):
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _claim_is_live(record: dict[str, Any], now: datetime) -> bool:
    if "released_at" in record:
        return False
    last_heartbeat_at = _parse_utc(record.get("last_heartbeat_at"))
    lease_seconds = record.get("lease_seconds")
    if last_heartbeat_at is not None and isinstance(lease_seconds, int):
        return now - last_heartbeat_at <= timedelta(seconds=lease_seconds)
    return True


def _path_aliases(path: Path, roots: Iterable[Path]) -> set[str]:
    aliases = {path.as_posix()}
    try:
        aliases.add(path.resolve().as_posix())
    except OSError:
        pass
    for root in roots:
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            continue
        aliases.add(rel)
        aliases.add(f".hermes/active-work-ledger/{rel}")
    return aliases


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


def _load_valid_panes(paths: Iterable[Path]) -> tuple[list[RegistryRecord], list[ValidationError]]:
    records: list[RegistryRecord] = []
    errors: list[ValidationError] = []
    for record_path in iter_pane_registry_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(make_error(CODE_INVALID, record_path, "/", "pane-registry record must be a YAML mapping", CONTRACT))
            continue
        record_errors = validate_pane_registry_record(record, record_path)
        errors.extend(record_errors)
        if not record_errors:
            records.append(RegistryRecord(record_path, record))
    return records, errors


def _load_live_claim_index(paths: Iterable[Path], roots: Iterable[Path], now: datetime) -> dict[str, ClaimRecord]:
    index: dict[str, ClaimRecord] = {}
    for record_path in iter_active_work_ledger_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError:
            continue
        if not isinstance(record, dict) or record.get("record_type") != "claim":
            continue
        if validate_active_work_ledger_record(record, record_path):
            continue
        if not _claim_is_live(record, now):
            continue
        item = ClaimRecord(record_path, record)
        for alias in _path_aliases(record_path, roots):
            index[alias] = item
    return index


def _load_container_index(paths: Iterable[Path], roots: Iterable[Path]) -> dict[str, ContainerRecord]:
    index: dict[str, ContainerRecord] = {}
    for record_path in iter_container_instance_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError:
            continue
        if not isinstance(record, dict):
            continue
        if validate_container_instance(record, record_path):
            continue
        item = ContainerRecord(record_path, record)
        for alias in _path_aliases(record_path, roots):
            index[alias] = item
        instance_id = record.get("instance_id")
        if isinstance(instance_id, str):
            index[instance_id] = item
    return index


def _resolve_ref(ref: Any, index: dict[str, Any]) -> Any | None:
    if not isinstance(ref, str) or not ref:
        return None
    if ref in index:
        return index[ref]
    normalized = ref[2:] if ref.startswith("./") else ref
    if normalized in index:
        return index[normalized]
    suffix = "/" + normalized
    for candidate_ref, item in index.items():
        if candidate_ref.endswith(suffix):
            return item
    return None


def _ledger_binding_errors(panes: Iterable[RegistryRecord], claim_index: dict[str, ClaimRecord]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for item in panes:
        record = item.record
        if record.get("status") not in LIVE_STATUSES:
            continue
        claim = _resolve_ref(record.get("claim_ref"), claim_index)
        if claim is None:
            errors.append(
                make_error(
                    CODE_LEDGER_BINDING,
                    item.path,
                    "claim_ref",
                    "live pane must bind to an existing live unreleased Active-Work Ledger claim",
                    CONTRACT,
                )
            )
            continue
        if claim.record.get("controller_id") != record.get("controller_id") or claim.record.get("lane_id") != record.get("lane_id"):
            errors.append(
                make_error(
                    CODE_LEDGER_BINDING,
                    item.path,
                    "claim_ref",
                    "live pane claim_ref must match controller_id and lane_id",
                    CONTRACT,
                )
            )
    return errors


def _duplicate_live_pane_errors(panes: Iterable[RegistryRecord]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    seen: dict[tuple[str, str], RegistryRecord] = {}
    for item in panes:
        record = item.record
        if record.get("status") not in DUPLICATE_REFUSAL_STATUSES:
            continue
        key = (str(record.get("claim_ref", "")), str(record.get("role", "")))
        existing = seen.get(key)
        if existing is None:
            seen[key] = item
            continue
        errors.append(
            make_error(
                CODE_DUPLICATE_LIVE_PANE,
                item.path,
                "role",
                f"duplicate live pane for claim_ref={key[0]!r} role={key[1]!r}; existing record {existing.path}",
                CONTRACT,
            )
        )
    return errors


def _container_binding_errors(
    panes: Iterable[RegistryRecord],
    container_index: dict[str, ContainerRecord],
    claim_index: dict[str, ClaimRecord],
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for item in panes:
        instance_ref = item.record.get("container_instance_ref")
        instance_id = item.record.get("container_instance_id")
        if not instance_ref and not instance_id:
            continue

        instance = _resolve_ref(instance_ref, container_index)
        if instance is None and instance_id:
            instance = _resolve_ref(instance_id, container_index)
        if instance is None:
            errors.append(
                make_error(
                    CODE_CONTAINER_BINDING,
                    item.path,
                    "container_instance_ref",
                    "container_instance_ref/container_instance_id must point to an existing valid container-instance record",
                    CONTRACT,
                )
            )
            continue

        if instance_id and instance.record.get("instance_id") != instance_id:
            errors.append(
                make_error(
                    CODE_CONTAINER_BINDING,
                    item.path,
                    "container_instance_id",
                    "container_instance_id must match the referenced container-instance record",
                    CONTRACT,
                )
            )
            continue

        claim = _resolve_ref(item.record.get("claim_ref"), claim_index)
        expected_claim_id = None if claim is None else claim.record.get("lane_id")
        if expected_claim_id is None:
            expected_claim_id = item.record.get("lane_id")
        if instance.record.get("claim_id") != expected_claim_id:
            errors.append(
                make_error(
                    CODE_CONTAINER_BINDING,
                    item.path,
                    "container_instance_ref",
                    "container-instance claim_id must match the Pane Registry claim context",
                    CONTRACT,
                )
            )
    return errors


@register(
    CHECK_NAME,
    [
        CODE_SCHEMA,
        CODE_ID_FORMAT,
        CODE_ROLE_STATUS,
        CODE_OPERATOR_VISIBLE,
        CODE_LEDGER_BINDING,
        CODE_DUPLICATE_LIVE_PANE,
        CODE_CONTAINER_BINDING,
        CODE_UNKNOWN_FIELDS,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    path_list = [Path(path) for path in paths]
    roots = _scan_roots(path_list)
    panes, errors = _load_valid_panes(path_list)
    now = datetime.now(UTC)
    claim_index = _load_live_claim_index(path_list, roots, now)
    container_index = _load_container_index(path_list, roots)
    errors.extend(_ledger_binding_errors(panes, claim_index))
    errors.extend(_duplicate_live_pane_errors(panes))
    errors.extend(_container_binding_errors(panes, container_index, claim_index))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
