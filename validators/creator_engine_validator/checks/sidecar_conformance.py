"""Wrapper sidecar conformance validation for US2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register
from .sidecar_utils import iter_sidecar_paths, sidecar_kind

SCHEMAS = {
    "spec": ("schemas/spec-wrapper-sidecar.schema.yaml", "docs/contracts/spec-wrapper-sidecar.md", "FR-009"),
    "plan": ("schemas/plan-wrapper-sidecar.schema.yaml", "docs/contracts/plan-wrapper-sidecar.md", "FR-012b"),
    "tasks": ("schemas/tasks-wrapper-sidecar.schema.yaml", "docs/contracts/tasks-wrapper-sidecar.md", "FR-012b"),
}


def _frontmatter_title(md_path: Path) -> str | None:
    if not md_path.exists():
        return None
    lines = md_path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    block: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        block.append(line)
    for line in block:
        if line.startswith("title:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def validate_sidecar(path: Path) -> CheckResult:
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    kind = sidecar_kind(path)
    if kind is None:
        return CheckResult(name="sidecar_conformance")
    schema_path, contract, code = SCHEMAS[kind]
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        errors.append(make_error(code, path, "", str(exc), contract))
        return CheckResult(name="sidecar_conformance", errors=tuple(errors))
    if not isinstance(data, dict):
        errors.append(make_error(code, path, "/", "sidecar must be a YAML mapping", contract))
        return CheckResult(name="sidecar_conformance", errors=tuple(errors))
    errors.extend(validate_with_schema(data, schema_path, path, code=code, contract=contract))

    if kind == "spec":
        md_path = path.with_name("spec.md")
        title = _frontmatter_title(md_path)
        sidecar_title = data.get("title")
        if title and sidecar_title and title.strip() != str(sidecar_title).strip():
            warnings.append(
                make_error(
                    "FR-009",
                    path,
                    "/title",
                    f"sidecar title differs from spec.md frontmatter title {title!r}; sidecar is canonical",
                    contract,
                )
            )
    if kind == "tasks" and isinstance(data.get("tasks"), list):
        seen_ids: dict[str, int] = {}
        for idx, task in enumerate(data["tasks"]):
            if not isinstance(task, dict):
                continue
            task_id = task.get("id")
            if isinstance(task_id, str):
                if task_id in seen_ids:
                    errors.append(make_error("FR-012b", path, f"/tasks/{idx}/id", f"duplicate task id {task_id!r}", contract))
                seen_ids[task_id] = idx
            author = task.get("author_actor_id")
            approver = task.get("approver_actor_id")
            if author and approver and author == approver:
                errors.append(make_error("FR-012b", path, f"/tasks/{idx}/approver_actor_id", "approver_actor_id must differ from author_actor_id", contract))
    return CheckResult(name="sidecar_conformance", errors=tuple(errors), warnings=tuple(warnings))


@register("sidecar_conformance", ["FR-009", "FR-012a", "FR-012b"])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []
    for sidecar in iter_sidecar_paths(paths):
        result = validate_sidecar(sidecar)
        errors.extend(result.errors)
        warnings.extend(result.warnings)
    return CheckResult(name="sidecar_conformance", errors=tuple(errors), warnings=tuple(warnings))
