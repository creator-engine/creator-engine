"""Seat-class policy record validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register
from .connector_substrate import _contains_secret, _pointer
from .mutation_class import BASELINE_NAMES_SET

CHECK_NAME = "seat_class_policy"
CONTRACT = "docs/contracts/seat-class-policy.md"
SCHEMA = "schemas/seat-class-policy.schema.yaml"
KIND_VALUE = "seat-class-policy-record"

CODE_SCHEMA = "VAL-SEAT-CLASS-SCHEMA"
CODE_INVALID = "VAL-SEAT-CLASS-INVALID"
CODE_DEFAULT = "VAL-SEAT-CLASS-DEFAULT"
CODE_RECURSION = "VAL-SEAT-CLASS-RECURSION"
CODE_MUTATION_CLASS = "VAL-SEAT-CLASS-MUTATION"
CODE_SECRET = "VAL-SEAT-CLASS-SECRET"


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".yml", ".yaml"}


def _record_is_policy(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_seat_class_policy_records(paths: Iterable[Path]) -> list[Path]:
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
            if not _record_is_policy(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_seat_class_policy(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))

    if record.get("default_seat_class") != "foreman":
        errors.append(make_error(
            CODE_DEFAULT,
            path,
            _pointer(("default_seat_class",)),
            "default_seat_class must be foreman; seats fail closed to foreman on absence or unknown values",
            CONTRACT,
        ))

    recursion = record.get("recursion")
    max_depth = recursion.get("max_depth") if isinstance(recursion, dict) else None
    if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth < 1:
        errors.append(make_error(
            CODE_RECURSION,
            path,
            _pointer(("recursion", "max_depth")),
            "recursion.max_depth must be an integer >= 1 for depth-bounded foreman recursion",
            CONTRACT,
        ))

    classes = record.get("delegation_required_mutation_classes")
    if isinstance(classes, list):
        for idx, mutation_class in enumerate(classes):
            if mutation_class not in BASELINE_NAMES_SET:
                errors.append(make_error(
                    CODE_MUTATION_CLASS,
                    path,
                    _pointer(("delegation_required_mutation_classes", idx)),
                    "delegation_required_mutation_classes entries must be baseline mutation_class names",
                    CONTRACT,
                ))

    if _contains_secret(record):
        errors.append(make_error(
            CODE_SECRET,
            path,
            "/",
            "seat-class-policy records must not carry secret or credential values",
            CONTRACT,
        ))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_INVALID, CODE_DEFAULT, CODE_RECURSION, CODE_MUTATION_CLASS, CODE_SECRET],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_seat_class_policy_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            continue
        errors.extend(validate_seat_class_policy(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))

