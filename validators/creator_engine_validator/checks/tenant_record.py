"""Tenant-record schema validation.

Validates tenant records against ``schemas/tenant-record.schema.yaml``. A YAML
file is a candidate tenant record when its loaded mapping has
``kind: tenant-record``. The validator is intentionally schema-only and
fail-closed: unknown fields, missing required sections, raw credential values,
bad enums, and bad ratification digests are refused by the schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "tenant_record"
CONTRACT = "validators/creator_engine_validator/schemas/tenant-record.schema.yaml"
SCHEMA = "schemas/tenant-record.schema.yaml"
KIND_VALUE = "tenant-record"
CODE_SCHEMA = "TENANT-RECORD-SCHEMA"
CODE_INVALID = "TENANT-RECORD-INVALID"


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_tenant_record(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_tenant_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate tenant-record files under ``paths``."""
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
            if not _record_is_tenant_record(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_tenant_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one tenant record against the tenant-record schema."""
    return validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)


@register(CHECK_NAME, [CODE_SCHEMA, CODE_INVALID])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_tenant_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(make_error(
                CODE_INVALID,
                record_path,
                "/",
                "tenant record must be a YAML mapping",
                CONTRACT,
            ))
            continue
        errors.extend(validate_tenant_record(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
