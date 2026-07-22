"""Deferred-work ledger schema validation and mandatory read-back ratchet.

The ledger is a repository-tracked inventory of agent-resolvable residue.  It
is distinct from human-decision waiting lists: entries must be triaged into the
ratified four-way partition and periodically read back into the work belt.
This validator is deliberately read-only; belt actuation remains a later seam.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "deferred_work_ledger"
CONTRACT = "docs/design/deferred-work-ledger.md"
SCHEMA = "schemas/deferred-work-ledger.schema.yaml"
LEDGER_RELATIVE = Path(".ce/deferred/ledger.yaml")
KIND_VALUE = "deferred-work-ledger"
CODE_SCHEMA = "CE604-001"
CODE_READ_BACK_STALE = "CE604-002"
CODE_INVALID = "deferred_work_ledger_invalid"


def _repo_root_for(path: Path) -> Path | None:
    """Find a checkout containing the tracked deferred-work ledger seed."""
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / LEDGER_RELATIVE).is_file():
            return candidate
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def validate_deferred_work_ledger(
    ledger: dict[str, Any], path: Path, *, now: datetime | None = None
) -> list[ValidationError]:
    """Validate shape, then reject entries not read within their declared budget."""
    errors = list(validate_with_schema(ledger, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    if errors:
        return errors

    effective_now = now or datetime.now(UTC)
    threshold = ledger["read_back_max_age_days"]
    for index, entry in enumerate(ledger["entries"]):
        last_read = _parse_timestamp(entry["last_read_at"])
        if last_read is None:  # schema should make this unreachable; retain fail-closed behavior.
            errors.append(
                make_error(CODE_READ_BACK_STALE, path, f"entries/{index}/last_read_at", "last_read_at is unreadable", CONTRACT)
            )
            continue
        age_seconds = (effective_now - last_read.astimezone(UTC)).total_seconds()
        if age_seconds > threshold * 24 * 60 * 60:
            errors.append(
                make_error(
                    CODE_READ_BACK_STALE,
                    path,
                    f"entries/{index}/last_read_at",
                    f"entry exceeds its {threshold}-day read-back budget; re-triage and record a new read-back marker",
                    CONTRACT,
                )
            )
    return errors


def _ledger_for_root(root: Path) -> Path | None:
    candidate = root / LEDGER_RELATIVE
    return candidate if candidate.is_file() else None


@register(CHECK_NAME, [CODE_SCHEMA, CODE_READ_BACK_STALE, CODE_INVALID])
def run(paths: Iterable[Path], *, now: datetime | None = None) -> CheckResult:
    """Validate each discovered checkout's one canonical deferred-work ledger."""
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        root = _repo_root_for(Path(raw))
        if root is not None and root.resolve() not in seen:
            seen.add(root.resolve())
            roots.append(root)

    errors: list[ValidationError] = []
    for root in roots:
        ledger_path = _ledger_for_root(root)
        if ledger_path is None:
            continue
        try:
            ledger = load_yaml(ledger_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, ledger_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(ledger, dict) or ledger.get("kind") != KIND_VALUE:
            errors.append(
                make_error(CODE_INVALID, ledger_path, "/", "deferred-work ledger must be a matching YAML mapping", CONTRACT)
            )
            continue
        errors.extend(validate_deferred_work_ledger(ledger, ledger_path, now=now))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
