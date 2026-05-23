"""Side-Effect Ledger substrate validation (PCO Slice 4).

This module validates redaction-safe Side-Effect Ledger records and
their optional bindings. It intentionally stays in schema/examples/
validator territory: no runtime observation hooks, pane spawning,
GitHub/CI/deploy/provider/MCP/plugin mutations, fan-in, or Integration
Queue implementation.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register
from .active_work_ledger_schema import iter_active_work_ledger_records, validate_active_work_ledger_record
from .pane_registry import iter_pane_registry_records, validate_pane_registry_record

CHECK_NAME = "side_effect_ledger"
CONTRACT = "docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md"
SCHEMA = "schemas/side-effect-ledger.schema.yaml"
KIND_VALUE = "side-effect-ledger-record"

CODE_SCHEMA = "PCO-055"
CODE_LEDGER_BINDING = "PCO-056"
CODE_EFFECT_ID_UNIQUE = "PCO-057"
CODE_ENUMS = "PCO-058"
CODE_REDACTION_SAFE = "PCO-059"
CODE_PANE_BINDING = "PCO-060"
CODE_COMPLETION_REPORT_BINDING = "PCO-061"
CODE_INTEGRATION_QUEUE_BINDING = "PCO-062"
CODE_STRICT_AND_TMP_SKIP = "PCO-063"
CODE_INVALID = "side_effect_ledger_invalid_record"

EFFECT_KINDS = {
    "github_mutation",
    "git_mutation",
    "tracked_file_change",
    "external_tracker_mutation",
    "runtime_process_action",
    "container_action",
    "provider_mcp_plugin_config_change",
    "network_ci_deploy_action",
    "credential_secret_adjacent_event",
}
EFFECT_STATUSES = {"requested", "started", "succeeded", "failed", "cancelled", "observed", "unknown"}
SECRET_KEY_TOKENS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "private_key",
    "secret",
    "session_cookie",
    "token",
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b[A-Za-z0-9+/]{32,}={0,2}\b"),
)


@dataclass(frozen=True)
class SideEffectRecord:
    path: Path
    record: dict[str, Any]


@dataclass(frozen=True)
class BoundRecord:
    path: Path
    record: dict[str, Any]


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_side_effect(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_side_effect_ledger_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Side-Effect Ledger files under ``paths``."""
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
            if not _record_is_side_effect(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def _enum_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(record.get("effect_kind"), str) and record["effect_kind"] not in EFFECT_KINDS:
        errors.append(make_error(CODE_ENUMS, path, "effect_kind", "effect_kind must match the Side-Effect Ledger taxonomy", CONTRACT))
    if isinstance(record.get("effect_status"), str) and record["effect_status"] not in EFFECT_STATUSES:
        errors.append(make_error(CODE_ENUMS, path, "effect_status", "effect_status must match the Side-Effect Ledger status enum", CONTRACT))
    return errors


def _unsafe_secret_fields(value: Any, path: Path, prefix: str = "") -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            child_prefix = f"{prefix}.{key_text}" if prefix else key_text
            if any(token in key_lower for token in SECRET_KEY_TOKENS):
                errors.append(
                    make_error(
                        CODE_REDACTION_SAFE,
                        path,
                        child_prefix,
                        "Side-Effect Ledger records must use redaction-safe references, not secret-bearing fields",
                        CONTRACT,
                    )
                )
            errors.extend(_unsafe_secret_fields(child, path, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_unsafe_secret_fields(child, path, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                errors.append(
                    make_error(
                        CODE_REDACTION_SAFE,
                        path,
                        prefix,
                        "Side-Effect Ledger records must not store obvious secret-shaped payloads",
                        CONTRACT,
                    )
                )
                break
    return errors


def validate_side_effect_ledger_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one Side-Effect Ledger record against schema and local predicates."""
    errors = list(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    for error in tuple(errors):
        if "Unevaluated properties" in error.message:
            errors.append(
                make_error(
                    CODE_STRICT_AND_TMP_SKIP,
                    path,
                    "/",
                    "Side-Effect Ledger records refuse unknown fields",
                    CONTRACT,
                )
            )
    errors.extend(_enum_errors(record, path))
    for field in ("details", "evidence_refs", "subject_ref"):
        if field in record:
            errors.extend(_unsafe_secret_fields(record[field], path, field))
    return errors


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


def _path_aliases(path: Path, roots: Iterable[Path]) -> set[str]:
    aliases = {path.as_posix()}
    try:
        resolved = path.resolve()
        aliases.add(resolved.as_posix())
    except OSError:
        resolved = None
    for root in roots:
        if resolved is None:
            continue
        try:
            rel = resolved.relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            continue
        aliases.add(rel)
        aliases.add(f".hermes/active-work-ledger/{rel}")
    return aliases


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


def _resolve_file_ref(ref: Any, roots: Iterable[Path]) -> Path | None:
    if not isinstance(ref, str) or not ref:
        return None
    candidates = [Path(ref), Path.cwd() / ref]
    for root in roots:
        candidates.append(root / ref)
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _sha256_of_file(path: Path) -> str | None:
    try:
        with path.open("rb") as fh:
            hasher = hashlib.sha256()
            for chunk in iter(lambda: fh.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        return None


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or value.startswith(("commit:", "source-controlled:")):
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _load_side_effects(paths: Iterable[Path]) -> tuple[list[SideEffectRecord], list[ValidationError]]:
    records: list[SideEffectRecord] = []
    errors: list[ValidationError] = []
    for record_path in iter_side_effect_ledger_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(make_error(CODE_INVALID, record_path, "/", "side-effect-ledger record must be a YAML mapping", CONTRACT))
            continue
        record_errors = validate_side_effect_ledger_record(record, record_path)
        errors.extend(record_errors)
        if not record_errors:
            records.append(SideEffectRecord(record_path, record))
    return records, errors


def _load_claim_index(paths: Iterable[Path], roots: Iterable[Path]) -> dict[str, BoundRecord]:
    index: dict[str, BoundRecord] = {}
    for record_path in iter_active_work_ledger_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError:
            continue
        if not isinstance(record, dict) or record.get("record_type") != "claim":
            continue
        if validate_active_work_ledger_record(record, record_path):
            continue
        item = BoundRecord(record_path, record)
        for alias in _path_aliases(record_path, roots):
            index[alias] = item
    return index


def _load_pane_index(paths: Iterable[Path], roots: Iterable[Path]) -> dict[str, BoundRecord]:
    index: dict[str, BoundRecord] = {}
    for record_path in iter_pane_registry_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError:
            continue
        if not isinstance(record, dict) or validate_pane_registry_record(record, record_path):
            continue
        item = BoundRecord(record_path, record)
        for alias in _path_aliases(record_path, roots):
            index[alias] = item
    return index


def _claim_binding_errors(records: Iterable[SideEffectRecord], claim_index: dict[str, BoundRecord]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for item in records:
        claim = _resolve_ref(item.record.get("claim_ref"), claim_index)
        if claim is None:
            errors.append(make_error(CODE_LEDGER_BINDING, item.path, "claim_ref", "side-effect record must bind to a discovered Active-Work Ledger claim", CONTRACT))
            continue
        for field in ("controller_id", "lane_id"):
            if claim.record.get(field) != item.record.get(field):
                errors.append(make_error(CODE_LEDGER_BINDING, item.path, "claim_ref", "claim_ref must match controller_id and lane_id", CONTRACT))
                break
    return errors


def _effect_id_uniqueness_errors(records: Iterable[SideEffectRecord]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    seen: dict[tuple[str, str, str, str], SideEffectRecord] = {}
    for item in records:
        occurred_at = _parse_utc(item.record.get("occurred_at"))
        if occurred_at is None:
            continue
        key = (
            str(item.record.get("controller_id", "")),
            str(item.record.get("lane_id", "")),
            occurred_at.date().isoformat(),
            str(item.record.get("effect_id", "")),
        )
        existing = seen.get(key)
        if existing is None:
            seen[key] = item
            continue
        errors.append(
            make_error(
                CODE_EFFECT_ID_UNIQUE,
                item.path,
                "effect_id",
                f"effect_id duplicates {existing.path} within controller_id/lane_id/UTC day",
                CONTRACT,
            )
        )
    return errors


def _pane_binding_errors(records: Iterable[SideEffectRecord], pane_index: dict[str, BoundRecord]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for item in records:
        if not item.record.get("pane_ref"):
            continue
        pane = _resolve_ref(item.record.get("pane_ref"), pane_index)
        if pane is None:
            errors.append(make_error(CODE_PANE_BINDING, item.path, "pane_ref", "pane_ref must point to an existing valid Pane Registry record when resolvable", CONTRACT))
            continue
        for field in ("controller_id", "lane_id", "claim_ref"):
            if pane.record.get(field) != item.record.get(field):
                errors.append(make_error(CODE_PANE_BINDING, item.path, "pane_ref", "pane_ref context must match controller_id, lane_id, and claim_ref", CONTRACT))
                break
    return errors


def _completion_report_errors(records: Iterable[SideEffectRecord], roots: Iterable[Path]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for item in records:
        ref = item.record.get("completion_report_ref")
        if not ref:
            continue
        report_path = _resolve_file_ref(ref, roots)
        if report_path is None:
            continue
        try:
            report = load_yaml(report_path)
        except LoaderError:
            report = None
        if isinstance(report, dict):
            for field in ("controller_id", "lane_id"):
                if report.get(field) != item.record.get(field):
                    errors.append(make_error(CODE_COMPLETION_REPORT_BINDING, item.path, "completion_report_ref", "completion report context must match controller_id and lane_id", CONTRACT))
                    break
        declared_sha = item.record.get("completion_report_sha256")
        if isinstance(declared_sha, str):
            actual_sha = _sha256_of_file(report_path)
            if actual_sha is not None and actual_sha != declared_sha.lower():
                errors.append(make_error(CODE_COMPLETION_REPORT_BINDING, item.path, "completion_report_sha256", "completion_report_sha256 must match the referenced file bytes", CONTRACT))
    return errors


def _integration_queue_results(records: Iterable[SideEffectRecord], roots: Iterable[Path]) -> tuple[list[ValidationError], list[ValidationError]]:
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    for item in records:
        ref = item.record.get("integration_queue_ref")
        if not ref:
            continue
        queue_path = _resolve_file_ref(ref, roots)
        if queue_path is None:
            warnings.append(make_error(CODE_INTEGRATION_QUEUE_BINDING, item.path, "integration_queue_ref", "Integration Queue binding is reserved for Slice 6 and not yet enforced", CONTRACT))
            continue
        try:
            queue_record = load_yaml(queue_path)
        except LoaderError:
            continue
        if not isinstance(queue_record, dict):
            continue
        for field in ("controller_id", "lane_id", "claim_ref"):
            if field in queue_record and queue_record.get(field) != item.record.get(field):
                errors.append(make_error(CODE_INTEGRATION_QUEUE_BINDING, item.path, "integration_queue_ref", "resolvable Integration Queue context must match controller_id, lane_id, and claim_ref", CONTRACT))
                break
    return errors, warnings


@register(
    CHECK_NAME,
    [
        CODE_SCHEMA,
        CODE_LEDGER_BINDING,
        CODE_EFFECT_ID_UNIQUE,
        CODE_ENUMS,
        CODE_REDACTION_SAFE,
        CODE_PANE_BINDING,
        CODE_COMPLETION_REPORT_BINDING,
        CODE_INTEGRATION_QUEUE_BINDING,
        CODE_STRICT_AND_TMP_SKIP,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    path_list = [Path(path) for path in paths]
    roots = _scan_roots(path_list)
    records, errors = _load_side_effects(path_list)
    claim_index = _load_claim_index(path_list, roots)
    pane_index = _load_pane_index(path_list, roots)
    errors.extend(_claim_binding_errors(records, claim_index))
    errors.extend(_effect_id_uniqueness_errors(records))
    errors.extend(_pane_binding_errors(records, pane_index))
    errors.extend(_completion_report_errors(records, roots))
    queue_errors, warnings = _integration_queue_results(records, roots)
    errors.extend(queue_errors)
    return CheckResult(name=CHECK_NAME, errors=tuple(errors), warnings=tuple(warnings))
