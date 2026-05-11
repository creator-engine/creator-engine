"""Definition of Ready validation for US2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .sidecar_utils import iter_sidecar_paths

CONTRACT = "docs/contracts/definition-of-ready.md"
READY_OR_LATER = {"ready", "in_progress", "verified", "ratified", "done"}


def _missing_ready_fields(data: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not data.get("scope"):
        missing.append("/scope")
    acceptance = data.get("acceptance_criteria")
    if not isinstance(acceptance, list) or not acceptance:
        missing.append("/acceptance_criteria")
    verification = data.get("verification")
    if not isinstance(verification, dict) or not verification.get("method"):
        missing.append("/verification/method")
    if not isinstance(verification, dict) or not isinstance(verification.get("evidence_refs"), list) or not verification.get("evidence_refs"):
        missing.append("/verification/evidence_refs")
    return missing


def validate_definition_of_ready(path: Path, data: dict[str, Any]) -> list[ValidationError]:
    status = data.get("status")
    if status not in READY_OR_LATER:
        return []
    return [
        make_error("FR-013", path, field, "ready-or-later spec is missing required Definition of Ready field", CONTRACT)
        for field in _missing_ready_fields(data)
    ]


@register("definition_of_ready", ["FR-013"])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for sidecar in iter_sidecar_paths(paths, kind="spec"):
        try:
            data = load_yaml(sidecar)
        except LoaderError as exc:
            errors.append(make_error("FR-013", sidecar, "", str(exc), CONTRACT))
            continue
        if isinstance(data, dict):
            errors.extend(validate_definition_of_ready(sidecar, data))
    return CheckResult(name="definition_of_ready", errors=tuple(errors))
