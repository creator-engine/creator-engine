"""Worktree Lease schema validation (PCO Slice 2A).

Validates Worktree Lease records against
``schemas/worktree-lease.schema.yaml``.

Scope discipline — Slice 2A is **record/validate only**:

* this check validates one record at a time against the schema;
* it MUST NOT cross-check lease/lease overlap, lease/claim coverage,
  or any other cross-record invariant beyond the structural per-record
  shape. The Slice 1/2 ``active_work_ledger_conflicts`` check is
  additively extended with the lease-aware predicates (``PCO-021``,
  ``PCO-022``, ``PCO-023``), gated on the discovery of at least one
  valid lease record in the scanned tree so that trees with zero
  lease records preserve Slice 1/2 behavior unchanged.

A file is treated as a candidate Worktree Lease record when it
satisfies all of:

* YAML extension (``.yml`` / ``.yaml``);
* not under a ``schemas/`` or ``templates/`` directory;
* its path basename does NOT contain ``".tmp."`` (atomic-write
  temp files are skipped, mirroring the Slice 0 ledger discipline);
* the loaded YAML is a mapping whose ``kind`` field equals
  ``worktree-lease-record``.

Failures cite ``PCO-020`` (Worktree Lease record contract) and the
prose contract at ``docs/operations/WORKTREE_LEASE_PROTOCOL.md``.
Non-schema structural failures (file not a YAML mapping) cite
``worktree_lease_invalid_record`` to keep schema violations distinct
from structural pre-validation failures, mirroring the distinction
used by ``active_work_ledger_schema``.

See:
  - ``docs/operations/WORKTREE_LEASE_PROTOCOL.md``
  - ``docs/architecture/parallel-controller-orchestration.md``
  - ``schemas/worktree-lease.schema.yaml``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "worktree_lease_schema"
CONTRACT = "docs/operations/WORKTREE_LEASE_PROTOCOL.md"
SCHEMA = "schemas/worktree-lease.schema.yaml"
KIND_VALUE = "worktree-lease-record"
CODE_SCHEMA = "PCO-020"
CODE_INVALID = "worktree_lease_invalid_record"


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    if "schemas" in parts or "templates" in parts:
        return True
    return False


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_lease(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_worktree_lease_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Worktree Lease files under ``paths``."""
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
            if not _record_is_lease(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_worktree_lease_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one record against the Worktree Lease schema.

    Slice 2A scope: schema validation only. No cross-record checks.
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
    for record_path in iter_worktree_lease_records(paths):
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
                    "worktree-lease record must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_worktree_lease_record(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
