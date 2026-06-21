"""Work-sizing record schema check."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from ..work_sizing import size_ceremony
from . import register

CHECK_NAME = "work_sizing"
CONTRACT = "schemas/work-sizing.schema.yaml"
SCHEMA = "schemas/work-sizing.schema.yaml"
KIND_VALUE = "sizing-record"

CODE_SCHEMA = "VAL-WORK-SIZING-SCHEMA"
CODE_INVALID = "VAL-WORK-SIZING-INVALID"
DERIVED_FIELDS = ("artifact_set", "decomposition_depth", "ratification_gates", "adr_required")


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_work_sizing(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_work_sizing_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate work-sizing record files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p) and not _is_under_excluded(p) and not _is_tmp_artifact(p)
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
            if not _record_is_work_sizing(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_work_sizing(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one work-sizing record against schema and deterministic projection."""
    errors = validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)
    if errors:
        return errors
    try:
        expected = size_ceremony(str(record["work_class"]), str(record["mutation_class"]))
    except (KeyError, ValueError):
        return errors
    for field in DERIVED_FIELDS:
        if record.get(field) != expected[field]:
            errors.append(make_error(
                CODE_INVALID,
                path,
                field,
                f"{field} must equal size_ceremony(work_class, mutation_class)",
                CONTRACT,
            ))
    return errors


@register(CHECK_NAME, [CODE_SCHEMA, CODE_INVALID])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_work_sizing_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            continue
        errors.extend(validate_work_sizing(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
