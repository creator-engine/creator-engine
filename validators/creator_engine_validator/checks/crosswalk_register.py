"""v1 -> v2 Crosswalk Register validation (G2.001.4, FR-018 / RV2-001-018).

Validates the authoritative v1 -> v2 crosswalk register
(``specs/v2/_crosswalk.yml``) and any well-formed crosswalk-register fixture
against ``schemas/crosswalk-register.schema.yaml`` plus the predicates the
schema alone cannot express:

* schema identity — the record declares ``creator-engine/crosswalk-register``;
* authoritative — the register asserts ``authoritative: true`` (Q-C3, OD-08);
* canonical mappings — the core mapping groups (roles, state_paths,
  feature_labels, sidecars) are present and non-empty;
* derived-supersedes — no ``derived_material_note`` declares that derived
  ``.ce/crosswalks/`` material supersedes the tracked register;
* context-disposition — the v1 archived/import context is never declared to be
  emitted by new v2 artifacts.

The check is read-only: it loads YAML and validates. It performs no migration,
no network access, and no filesystem mutation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "crosswalk_register"
CONTRACT = "specs/v2/001-v2-foundation-substrate/spec.ce.yml#required_validation/VAL-CROSSWALK-AUTHORITATIVE"
SCHEMA = "schemas/crosswalk-register.schema.yaml"
SCHEMA_IDENTITY = "creator-engine/crosswalk-register"

# Failure codes (substrings tie back to the spec.ce.yml VAL-CROSSWALK-* IDs).
CODE_SCHEMA_IDENTITY = "VAL-CROSSWALK-SCHEMA-IDENTITY"
CODE_SCHEMA = "VAL-CROSSWALK-SCHEMA"
CODE_AUTHORITATIVE = "VAL-CROSSWALK-AUTHORITATIVE"
CODE_CANONICAL_MAPPING = "VAL-CROSSWALK-CANONICAL-MAPPING"
CODE_DERIVED_SUPERSEDES = "VAL-CROSSWALK-DERIVED-SUPERSEDES"
CODE_CONTEXT_DISPOSITION = "VAL-CROSSWALK-CONTEXT-DISPOSITION"

# The canonical crosswalk register lives at this filename; the formal mapping
# groups the register must carry to be a usable v1 -> v2 crosswalk.
CROSSWALK_FILENAMES = frozenset({"_crosswalk.yml", "_crosswalk.yaml"})
REQUIRED_MAPPING_GROUPS = ("roles", "state_paths", "feature_labels", "sidecars")

# Negations that make a "...emitted by ... v2..." archived-import rule compliant
# (the archived/import context is readable but never emitted by new v2 work).
_EMISSION_NEGATIONS = ("never", "not emit", "no emit", "not be emit", "must not")


def _is_empty(value: Any) -> bool:
    return value is None or value == [] or value == {} or value == ""


def _authoritative_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    if record.get("authoritative") is not True:
        return [
            make_error(
                CODE_AUTHORITATIVE,
                path,
                "/authoritative",
                "crosswalk register must assert authoritative: true (Q-C3, OD-08); "
                "the tracked register is authoritative over derived material",
                CONTRACT,
            )
        ]
    return []


def _canonical_mapping_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    missing = [group for group in REQUIRED_MAPPING_GROUPS if _is_empty(record.get(group))]
    if missing:
        return [
            make_error(
                CODE_CANONICAL_MAPPING,
                path,
                "/",
                "crosswalk register is missing required canonical mapping groups: "
                f"{missing}",
                CONTRACT,
            )
        ]
    return []


def _derived_supersedes_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    note = record.get("derived_material_note")
    if isinstance(note, str):
        low = note.lower()
        if "supersed" in low and "not supersed" not in low and "never supersed" not in low:
            return [
                make_error(
                    CODE_DERIVED_SUPERSEDES,
                    path,
                    "/derived_material_note",
                    "derived material must not supersede the tracked crosswalk register; "
                    "the register is authoritative and is not superseded by derived material",
                    CONTRACT,
                )
            ]
    return []


def _context_disposition_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    disposition = record.get("context_disposition")
    if not isinstance(disposition, dict):
        return []
    archived = disposition.get("v1_archived_import_context")
    if not isinstance(archived, dict):
        return []
    rules = archived.get("rules")
    if not isinstance(rules, list):
        return []
    for rule in rules:
        if not isinstance(rule, str):
            continue
        low = rule.lower()
        if "emit" in low and "v2" in low and not any(neg in low for neg in _EMISSION_NEGATIONS):
            return [
                make_error(
                    CODE_CONTEXT_DISPOSITION,
                    path,
                    "/context_disposition/v1_archived_import_context/rules",
                    "archived/import context must never be emitted by new v2 artifacts; "
                    f"offending rule: {rule!r}",
                    CONTRACT,
                )
            ]
    return []


def _validate_record(record: Any, path: Path) -> list[ValidationError]:
    if not isinstance(record, dict):
        return [
            make_error(
                CODE_SCHEMA_IDENTITY,
                path,
                "/",
                "crosswalk register must be a YAML mapping",
                CONTRACT,
            )
        ]
    if record.get("schema") != SCHEMA_IDENTITY:
        return [
            make_error(
                CODE_SCHEMA_IDENTITY,
                path,
                "/schema",
                f"crosswalk register must declare schema {SCHEMA_IDENTITY!r}, "
                f"got {record.get('schema')!r}",
                CONTRACT,
            )
        ]
    errors = list(
        validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)
    )
    errors.extend(_authoritative_errors(record, path))
    errors.extend(_canonical_mapping_errors(record, path))
    errors.extend(_derived_supersedes_errors(record, path))
    errors.extend(_context_disposition_errors(record, path))
    return errors


def validate_file(path: str | Path) -> list[ValidationError]:
    """Validate a single crosswalk-register file, returning its errors."""
    target = Path(path)
    try:
        record = load_yaml(target)
    except LoaderError as exc:
        return [make_error(CODE_SCHEMA_IDENTITY, target, "", str(exc), CONTRACT)]
    return _validate_record(record, target)


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _is_crosswalk_record(path: Path, data: Any) -> bool:
    if path.name in CROSSWALK_FILENAMES:
        return True
    return isinstance(data, dict) and data.get("schema") == SCHEMA_IDENTITY


def iter_crosswalk_register_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate crosswalk-register files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p)
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
            if not _is_crosswalk_record(candidate, data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


@register(
    CHECK_NAME,
    [
        CODE_SCHEMA_IDENTITY,
        CODE_SCHEMA,
        CODE_AUTHORITATIVE,
        CODE_CANONICAL_MAPPING,
        CODE_DERIVED_SUPERSEDES,
        CODE_CONTEXT_DISPOSITION,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_crosswalk_register_records(paths):
        errors.extend(validate_file(record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
