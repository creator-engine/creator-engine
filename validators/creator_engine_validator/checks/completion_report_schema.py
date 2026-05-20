"""Completion Report schema validation (PCO Slice 0.5).

Validates Completion Report artifacts against
``schemas/completion-report.schema.yaml``.

Scope discipline — Slice 0.5 is **record/validate only**:

* this check validates one report at a time against the schema;
* it MUST NOT implement the Hermes final-answer / send-blocking
  runtime hook (that is Slice 0.5R);
* it MUST NOT cross-check envelope→report pairing — that is the
  responsibility of the ``completion_report_required_for_envelope``
  check (CR-002).

A file is treated as a candidate Completion Report when it satisfies
all of:

* YAML extension (``.yml`` / ``.yaml``);
* not under a ``schemas/`` or ``templates/`` directory;
* its path basename does NOT contain ``".tmp."`` (atomic-write
  temp files are skipped, mirroring the active-work-ledger
  discovery rule);
* the loaded YAML is a mapping whose ``kind`` field equals
  ``completion-report``.

Failures cite ``CR-001`` (Completion Report record contract) and the
prose contract at ``docs/operations/COMPLETION_REPORT_PROTOCOL.md``.
Structural pre-validation failures (file not a YAML mapping) cite
``completion_report_invalid_record`` to keep schema violations
distinct from structural pre-validation failures, mirroring
``active_work_ledger_schema`` and ``handoff_schema``.

See:
  - ``docs/operations/COMPLETION_REPORT_PROTOCOL.md``
  - ``schemas/completion-report.schema.yaml``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "completion_report_schema"
CONTRACT = "docs/operations/COMPLETION_REPORT_PROTOCOL.md"
SCHEMA = "schemas/completion-report.schema.yaml"
KIND_VALUE = "completion-report"
CODE_SCHEMA = "CR-001"
CODE_INVALID = "completion_report_invalid_record"


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    if "schemas" in parts or "templates" in parts:
        return True
    return False


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_completion_report(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_completion_report_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Completion Report files under ``paths``."""
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
            if not _record_is_completion_report(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_completion_report_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one Completion Report record against the schema.

    Slice 0.5 scope: schema validation only. No envelope→report
    pairing (CR-002), no terminal-section cross-check (CR-003).
    """
    errors = validate_with_schema(
        record,
        SCHEMA,
        path,
        code=CODE_SCHEMA,
        contract=CONTRACT,
    )
    return list(errors)


@register(CHECK_NAME, [CODE_SCHEMA])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_completion_report_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(
                make_error(
                    CODE_INVALID,
                    record_path,
                    "/",
                    "completion-report record must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_completion_report_record(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
