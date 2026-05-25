"""State Version / Migration record validation (RV1-022, PCO v1 Gate 2).

Validates State Version / Migration records against
``schemas/state-version-record.schema.yaml`` plus the supported-version-window
predicate that the schema alone cannot express.

Gate 2 scope is substrate/validator-only. This check:

* validates one declarative record at a time;
* refuses stale state versions (below the minimum supported v1.0 layout) and
  future/unknown state versions (ahead of the current supported version);
* refuses invalid migration statuses (constrained enum, enforced by schema).

The record is declarative and validated only. It must not perform migrations.

Candidate discovery mirrors the existing PCO record validators: YAML files
outside ``schemas/`` and ``templates/`` whose loaded mapping has
``kind: state-version-record`` are scanned, while atomic ``*.tmp.*`` artifacts
are skipped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "state_version_record"
CONTRACT = "docs/operations/STATE_BOUNDARY_PROTOCOL.md"
SCHEMA = "schemas/state-version-record.schema.yaml"
KIND_VALUE = "state-version-record"

CODE_SCHEMA = "RV1-022"
CODE_STALE = "RV1-022-STALE"
CODE_INVALID = "state_version_record_invalid_record"

# v1.0 ships a single supported `.hermes/` governed state layout: version 1.
# A record below this is stale (the pre-bootstrap layout must be migrated
# forward); a record above this is an unknown future version this kernel
# cannot interpret.
CURRENT_STATE_VERSION = 1
MIN_SUPPORTED_STATE_VERSION = 1


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_state_version(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_state_version_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate State Version / Migration record files under ``paths``."""
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
            if not _record_is_state_version(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def _version_window_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    version = record.get("state_version")
    # Non-integer / bool values are reported by the schema check, not here.
    if not isinstance(version, int) or isinstance(version, bool):
        return []
    if version < MIN_SUPPORTED_STATE_VERSION:
        return [
            make_error(
                CODE_STALE,
                path,
                "/state_version",
                f"state_version {version} is stale (below minimum supported v1.0 layout "
                f"{MIN_SUPPORTED_STATE_VERSION}); the state must be migrated forward",
                CONTRACT,
            )
        ]
    if version > CURRENT_STATE_VERSION:
        return [
            make_error(
                CODE_STALE,
                path,
                "/state_version",
                f"state_version {version} is ahead of the current supported version "
                f"{CURRENT_STATE_VERSION}; this kernel cannot interpret it",
                CONTRACT,
            )
        ]
    return []


def validate_state_version_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one State Version / Migration record against RV1-022."""
    errors = list(
        validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)
    )
    errors.extend(_version_window_errors(record, path))
    return errors


@register(CHECK_NAME, [CODE_SCHEMA, CODE_STALE])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_state_version_records(paths):
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
                    "state-version-record must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_state_version_record(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
