"""DevOps privileged-action broker envelope validator check."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..devops_privileged_action_broker import (
    CODE_CAPABILITY,
    CODE_EXECUTION,
    CODE_SCHEMA,
    CODE_SECRET,
    validate_envelope,
)
from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "devops_privileged_action_broker"
CONTRACT = "docs/contracts/devops-privileged-action-broker.md"
KIND_FIELD = "privileged_action_envelope"


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".yml", ".yaml"}


def _has_envelope(document: Any) -> bool:
    return isinstance(document, dict) and KIND_FIELD in document


def iter_envelope_files(paths: Iterable[Path]) -> list[Path]:
    """Return YAML files carrying a top-level privileged-action envelope."""

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
                document = load_yaml(candidate)
            except LoaderError:
                continue
            if not _has_envelope(document):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


@register(
    CHECK_NAME,
    [
        CODE_SCHEMA,
        CODE_CAPABILITY,
        CODE_SECRET,
        CODE_EXECUTION,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_envelope_files(Path(path) for path in paths):
        try:
            document = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_SCHEMA, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(document, dict):
            errors.append(
                make_error(
                    CODE_SCHEMA,
                    record_path,
                    "/",
                    "privileged-action broker envelope file must be a YAML mapping",
                    CONTRACT,
                )
            )
            continue
        errors.extend(validate_envelope(document, instance_path=record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
