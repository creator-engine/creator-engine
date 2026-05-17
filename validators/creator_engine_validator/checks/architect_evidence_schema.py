"""Architect evidence schema validation.

Validates governed architect evidence records against
``schemas/architect-evidence.schema.yaml``.

A file is treated as a candidate architect-evidence record when it
satisfies all of:

* YAML extension (``.yml`` / ``.yaml``);
* not under a ``schemas/`` directory;
* the loaded YAML is a mapping whose ``architect_role_category`` field
  equals ``architect``.

Failures cite ``FR-001`` (machine-readable record contract) and the
prose contract at ``docs/contracts/architect-evidence.md`` per FR-027.

See:
  - ``docs/contracts/architect-evidence.md``
  - ``schemas/architect-evidence.schema.yaml``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "architect_evidence_schema"
CONTRACT = "docs/contracts/architect-evidence.md"
SCHEMA = "schemas/architect-evidence.schema.yaml"
ROLE_CATEGORY_VALUE = "architect"


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_architect_evidence(record: Any) -> bool:
    return (
        isinstance(record, dict)
        and record.get("architect_role_category") == ROLE_CATEGORY_VALUE
    )


def iter_architect_evidence_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate architect evidence files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p) and not _is_under_excluded(p)
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
            if not _record_is_architect_evidence(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_architect_evidence_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one record against the architect-evidence schema."""
    errors = validate_with_schema(
        record,
        SCHEMA,
        path,
        code="FR-001",
        contract=CONTRACT,
    )
    return list(errors)


@register(CHECK_NAME, ["FR-001"])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_architect_evidence_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error("FR-001", record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(
                make_error(
                    "FR-001",
                    record_path,
                    "/",
                    "architect evidence record must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_architect_evidence_record(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
