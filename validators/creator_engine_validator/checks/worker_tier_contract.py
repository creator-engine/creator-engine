"""ce-ops#244 governed worker-tier contract validator.

This check validates ``ce-worker-spawn-record`` files for first-class governed
in-process workers. It intentionally references the foreman dispatch contract
instead of revalidating or duplicating it here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "worker_tier_contract"
CONTRACT = "schemas/worker-tier-contract.schema.yaml"
SCHEMA = "schemas/worker-tier-contract.schema.yaml"
KIND = "ce-worker-spawn-record"

CODE_SCHEMA = "VAL-WORKER-TIER-SCHEMA"
CODE_ROLE = "VAL-WORKER-TIER-ROLE"
CODE_GOVERNANCE = "VAL-WORKER-TIER-GOVERNANCE"
CODE_CAPABILITY = "VAL-WORKER-TIER-CAPABILITY"
CODE_BOUNDS = "VAL-WORKER-TIER-BOUNDS"
CODE_RESULT = "VAL-WORKER-TIER-RESULT"
CODE_SURFACE = "VAL-WORKER-TIER-SURFACE"

ROLE_LANE_KIND = {
    "researcher": "read-only",
    "implementer": "implementation",
    "reviewer": "review",
}
ROLE_SURFACE_REFS = {
    "researcher": ".claude/agents/architect_research.md",
    "implementer": ".claude/agents/implementer.md",
    "reviewer": ".claude/agents/reviewer.md",
}
REQUIRED_PROHIBITED_CAPABILITIES = frozenset(
    {"push", "self_approve", "create_issues", "task_other_seats"}
)


def _pointer(parts: tuple[Any, ...]) -> str:
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _is_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".yml", ".yaml"}


def _is_worker_spawn_record(data: Any) -> bool:
    return isinstance(data, dict) and data.get("kind") == KIND


def iter_worker_tier_contract_records(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _is_yaml(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _is_yaml(p) and not _is_tmp_artifact(p)
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
            if not _is_worker_spawn_record(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def _contract(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("governed_worker_contract")
    return value if isinstance(value, dict) else {}


def _infer_repo_root_from_record_path(path: Path) -> Path | None:
    parts = path.parts
    try:
        index = parts.index(".ce")
    except ValueError:
        return None
    if index == 0:
        return Path(".")
    return Path(*parts[:index])


def _validate_role(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    contract = _contract(record)
    role = record.get("role")
    contract_role = contract.get("role")
    if role not in ROLE_LANE_KIND:
        errors.append(make_error(CODE_ROLE, path, "/role", "worker role must be one of researcher, implementer, reviewer", CONTRACT))
        return errors
    if contract_role != role:
        errors.append(make_error(CODE_ROLE, path, "/governed_worker_contract/role", "contract role must match the worker spawn record role", CONTRACT))
    lane_kind = record.get("lane_kind")
    if lane_kind != ROLE_LANE_KIND[role]:
        errors.append(make_error(CODE_ROLE, path, "/lane_kind", f"role {role!r} must map to lane_kind {ROLE_LANE_KIND[role]!r}", CONTRACT))
    return errors


def _validate_role_surface(record: dict[str, Any], path: Path, repo_root: Path | None) -> list[ValidationError]:
    role = record.get("role")
    expected = ROLE_SURFACE_REFS.get(str(role))
    actual = _contract(record).get("role_surface_ref")
    if expected is not None and actual != expected:
        return [
            make_error(
                CODE_SURFACE,
                path,
                "/governed_worker_contract/role_surface_ref",
                f"role {role!r} must reference existing role surface {expected!r}",
                CONTRACT,
            )
        ]
    if expected is not None and isinstance(actual, str) and repo_root is not None:
        surface = (repo_root / actual).resolve(strict=False)
        if not surface.is_file():
            return [
                make_error(
                    CODE_SURFACE,
                    path,
                    "/governed_worker_contract/role_surface_ref",
                    f"role {role!r} role_surface_ref {actual!r} must point to an existing role surface file",
                    CONTRACT,
                )
            ]
    return []


def _validate_governance(record: dict[str, Any], path: Path) -> list[ValidationError]:
    gov = _contract(record).get("inherited_governance")
    if not isinstance(gov, dict):
        return [make_error(CODE_GOVERNANCE, path, "/governed_worker_contract/inherited_governance", "worker contract must declare inherited governance", CONTRACT)]
    expected = {
        "ring": "ring_1",
        "refusal": "inherited",
        "envelope": "inherited",
        "ambient_credentials": "none",
    }
    errors: list[ValidationError] = []
    for key, value in expected.items():
        if gov.get(key) != value:
            errors.append(
                make_error(
                    CODE_GOVERNANCE,
                    path,
                    _pointer(("governed_worker_contract", "inherited_governance", key)),
                    f"inherited_governance.{key} must be {value!r}",
                    CONTRACT,
                )
            )
    return errors


def _validate_capabilities(record: dict[str, Any], path: Path) -> list[ValidationError]:
    contract = _contract(record)
    declared = contract.get("declared_capabilities")
    prohibited = contract.get("prohibited_capabilities")
    declared_set = {item for item in declared if isinstance(item, str)} if isinstance(declared, list) else set()
    prohibited_set = {item for item in prohibited if isinstance(item, str)} if isinstance(prohibited, list) else set()
    required = set(REQUIRED_PROHIBITED_CAPABILITIES)
    errors: list[ValidationError] = []
    missing = sorted(required - prohibited_set)
    if missing:
        errors.append(
            make_error(
                CODE_CAPABILITY,
                path,
                "/governed_worker_contract/prohibited_capabilities",
                f"prohibited_capabilities must include {sorted(required)}; missing {missing}",
                CONTRACT,
            )
        )
    forbidden_declared = sorted(declared_set & required)
    if forbidden_declared:
        errors.append(
            make_error(
                CODE_CAPABILITY,
                path,
                "/governed_worker_contract/declared_capabilities",
                f"worker declares prohibited capability/capabilities: {forbidden_declared}",
                CONTRACT,
            )
        )
    return errors


def _validate_bounds(record: dict[str, Any], path: Path) -> list[ValidationError]:
    bounds = _contract(record).get("bounds")
    if not isinstance(bounds, dict):
        return [make_error(CODE_BOUNDS, path, "/governed_worker_contract/bounds", "worker contract must declare capability bounds", CONTRACT)]
    false_flags = {
        "may_push": "push",
        "may_self_approve": "self-approve",
        "may_create_issues": "create issues",
        "may_task_other_seats": "task other seats",
        "may_receive_ambient_credentials": "receive ambient credentials",
    }
    errors: list[ValidationError] = []
    for key, label in false_flags.items():
        if bounds.get(key) is not False:
            errors.append(
                make_error(
                    CODE_BOUNDS,
                    path,
                    _pointer(("governed_worker_contract", "bounds", key)),
                    f"worker must not {label}; {key} must be false",
                    CONTRACT,
                )
            )
    depth = record.get("depth")
    record_max = record.get("max_depth")
    contract_max = bounds.get("max_depth")
    if not all(isinstance(value, int) for value in (depth, record_max, contract_max)):
        errors.append(make_error(CODE_BOUNDS, path, "/depth", "depth, max_depth, and bounds.max_depth must be integers", CONTRACT))
        return errors
    if contract_max != record_max:
        errors.append(make_error(CODE_BOUNDS, path, "/governed_worker_contract/bounds/max_depth", "bounds.max_depth must match the worker spawn record max_depth", CONTRACT))
    if depth < 1 or depth > record_max:
        errors.append(make_error(CODE_BOUNDS, path, "/depth", "worker depth must be within the spawn record max_depth bound", CONTRACT))
    return errors


def _validate_result(record: dict[str, Any], path: Path) -> list[ValidationError]:
    result = _contract(record).get("result_protocol")
    if not isinstance(result, dict) or result.get("returns") != "structured_result_to_foreman":
        return [
            make_error(
                CODE_RESULT,
                path,
                "/governed_worker_contract/result_protocol/returns",
                "worker must return a structured result to its foreman",
                CONTRACT,
            )
        ]
    return []


def validate_worker_tier_contract_record(
    record: dict[str, Any],
    path: Path,
    *,
    repo_root: Path | None = None,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    try:
        errors.extend(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=SCHEMA))
    except Exception as exc:  # pragma: no cover - environment guard
        errors.append(make_error(CODE_SCHEMA, path, "", f"schema validation failed: {exc}", SCHEMA))
    if not isinstance(record.get("governed_worker_contract"), dict):
        return errors
    inferred_repo_root = Path(repo_root) if repo_root is not None else _infer_repo_root_from_record_path(Path(path))
    errors.extend(_validate_role(record, path))
    errors.extend(_validate_role_surface(record, path, inferred_repo_root))
    errors.extend(_validate_governance(record, path))
    errors.extend(_validate_capabilities(record, path))
    errors.extend(_validate_bounds(record, path))
    errors.extend(_validate_result(record, path))
    return errors


def validate_worker_tier_contract_file(path: Path, *, repo_root: Path | None = None) -> list[ValidationError]:
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [make_error(CODE_SCHEMA, path, "", str(exc), SCHEMA)]
    if not isinstance(data, dict) or data.get("kind") != KIND:
        return []
    return validate_worker_tier_contract_record(data, Path(path), repo_root=repo_root)


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_ROLE, CODE_GOVERNANCE, CODE_CAPABILITY, CODE_BOUNDS, CODE_RESULT, CODE_SURFACE],
)
def run_worker_tier_contract(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in iter_worker_tier_contract_records(paths):
        errors.extend(validate_worker_tier_contract_file(file_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
