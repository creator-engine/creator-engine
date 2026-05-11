"""Duplicate spec id detection for US2."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .sidecar_utils import iter_sidecar_paths

CONTRACT = "docs/contracts/spec-wrapper-sidecar.md"


def find_duplicate_spec_ids(paths: Iterable[Path]) -> list[ValidationError]:
    seen: dict[str, Path] = {}
    errors: list[ValidationError] = []
    for sidecar in iter_sidecar_paths(paths, kind="spec"):
        try:
            data = load_yaml(sidecar)
        except LoaderError as exc:
            errors.append(make_error("FR-027a", sidecar, "", str(exc), CONTRACT))
            continue
        if not isinstance(data, dict):
            continue
        spec_id = data.get("id")
        if not isinstance(spec_id, str) or not spec_id:
            continue
        if spec_id in seen:
            errors.append(
                make_error(
                    "FR-027a",
                    sidecar,
                    "/id",
                    f"duplicate spec id {spec_id!r}; first seen at {seen[spec_id]}",
                    CONTRACT,
                )
            )
        else:
            seen[spec_id] = sidecar
    return errors


@register("duplicate_spec_id", ["FR-027a"])
def run(paths: Iterable[Path]) -> CheckResult:
    return CheckResult(name="duplicate_spec_id", errors=tuple(find_duplicate_spec_ids(paths)))
