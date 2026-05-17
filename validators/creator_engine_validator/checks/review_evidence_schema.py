"""Review evidence schema validation.

Validates governed review evidence records against
``schemas/review-evidence.schema.yaml``.

A file is treated as a candidate review-evidence record when it
satisfies all of:

* YAML extension (``.yml`` / ``.yaml``);
* not under a ``schemas/`` or ``templates/`` directory;
* the loaded YAML is a mapping whose ``reviewer_role_category`` field
  equals ``reviewer``.

Failures cite ``FR-001`` (machine-readable record contract) and the
prose contract at ``docs/contracts/review-evidence.md`` per FR-027.

See:
  - ``docs/contracts/review-evidence.md``
  - ``docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md``
  - ``schemas/review-evidence.schema.yaml``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "review_evidence_schema"
CONTRACT = "docs/contracts/review-evidence.md"
SCHEMA = "schemas/review-evidence.schema.yaml"
ROLE_CATEGORY_VALUE = "reviewer"


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_review_evidence(record: Any) -> bool:
    return (
        isinstance(record, dict)
        and record.get("reviewer_role_category") == ROLE_CATEGORY_VALUE
    )


def iter_review_evidence_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate review evidence files under ``paths``."""
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
            if not _record_is_review_evidence(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_review_evidence_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one record against the review-evidence schema."""
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
    for record_path in iter_review_evidence_records(paths):
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
                    "review evidence record must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_review_evidence_record(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
