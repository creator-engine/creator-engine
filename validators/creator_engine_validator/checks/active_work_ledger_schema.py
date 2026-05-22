"""Active-Work Ledger schema validation (PCO Slice 0; Slice 0.5; Slice 2I-S additive extensions).

Validates Active-Work Ledger records against
``schemas/active-work-ledger.schema.yaml``.

Scope discipline — Slice 0 is **record/validate only**:

* this check validates one record at a time against the schema;
* it MUST NOT cross-check lane uniqueness across files,
  ``worktree_path`` collisions between claims beyond noting that
  ``active_work_ledger_conflicts`` owns them, heartbeat
  monotonicity within a claim beyond field shape, event-log ordering,
  stale-record reclamation, or any other cross-record invariant. The
  Slice 1/2 conflict check is intentionally separate so this schema
  layer remains one-record validation.

Slice 0.5 additive extension: the schema now accepts
``schema_version`` ``"1"`` or ``"2"`` and recognises four additional
``event_kind`` values — ``gate_opened``, ``gate_closed``,
``completion_report_emitted``, ``gate_blocked`` — that bind the
event log to the Completion Report substrate. The change is purely
additive: v1 records continue to validate unchanged; this check's
discovery/scoping behaviour is unchanged.

Slice 2I-S additive extension: the schema now also accepts
``schema_version`` ``"3"`` and recognises three additional
``event_kind`` values — ``container_started``, ``container_stopped``,
``container_force_reaped`` — that bind the event log to the Worker
Container substrate. The ``details`` object additively accepts optional
container-event fields (``instance_id``, ``claim_id``, ``exit_code``,
``reason``, ``force_reaped_at``, ``elapsed_since_release_seconds``). The
change is purely additive: v1 and v2 records continue to validate
unchanged; this check's discovery/scoping behaviour is unchanged.

A file is treated as a candidate Active-Work Ledger record when it
satisfies all of:

* YAML extension (``.yml`` / ``.yaml``);
* not under a ``schemas/`` or ``templates/`` directory;
* its path basename does NOT contain ``".tmp."`` (atomic-write
  temp files are skipped, per protocol §l);
* the loaded YAML is a mapping whose ``kind`` field equals
  ``active-work-ledger-record``.

Failures cite ``PCO-001`` (Active-Work Ledger record contract) and
the prose contract at
``docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md``. Non-schema
structural failures (file not a YAML mapping) cite
``active_work_ledger_invalid_record`` to keep schema violations
distinct from structural pre-validation failures, mirroring the
distinction used by ``handoff_schema``.

See:
  - ``docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md``
  - ``docs/architecture/parallel-controller-orchestration.md``
  - ``schemas/active-work-ledger.schema.yaml``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "active_work_ledger_schema"
CONTRACT = "docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md"
SCHEMA = "schemas/active-work-ledger.schema.yaml"
KIND_VALUE = "active-work-ledger-record"
CODE_SCHEMA = "PCO-001"
CODE_INVALID = "active_work_ledger_invalid_record"


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    if "schemas" in parts or "templates" in parts:
        return True
    return False


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_ledger(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_active_work_ledger_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Active-Work Ledger files under ``paths``."""
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
            if not _record_is_ledger(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_active_work_ledger_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one record against the Active-Work Ledger schema.

    Slice 0 scope: schema validation only. No cross-record checks.
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
    for record_path in iter_active_work_ledger_records(paths):
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
                    "active-work-ledger record must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_active_work_ledger_record(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
