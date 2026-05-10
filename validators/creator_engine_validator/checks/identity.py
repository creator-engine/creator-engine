"""Tenant identity record validation for US1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "identity"
CONTRACT = "docs/contracts/identity-record.md"
SCHEMA = "schemas/identity-record.schema.yaml"
STORAGE_FIELDS = (
    "attestation_storage_path",
    "ratification_storage_path",
    "redaction_storage_path",
)


def _repo_root_for(path: Path) -> Path:
    for candidate in (path if path.is_dir() else path.parent, *path.parents):
        if (candidate / ".git").exists() or (candidate / "validators").exists():
            return candidate
    return Path.cwd()


def _is_under_malformed_examples(path: Path) -> bool:
    parts = path.parts
    return "examples" in parts and "malformed" in parts


def _is_identity_candidate(path: Path) -> bool:
    if not (path.is_file() and path.suffix in {".yml", ".yaml"}):
        return False
    if "schemas" in path.parts or "templates" in path.parts:
        return False
    return path.name == "identity-record.yml" or path.name == "identity-record.yaml" or path.name.startswith("identity-record.")


def iter_identity_records(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _is_identity_candidate(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("identity-record*.yml")) + sorted(path.rglob("identity-record*.yaml"))
                if _is_identity_candidate(p) and not _is_under_malformed_examples(p)
            ]
        else:
            candidates = []
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                records.append(candidate)
    return records


def _schema_errors(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors = validate_with_schema(
        record,
        SCHEMA,
        path,
        code="FR-001",
        contract=CONTRACT,
    )
    normalized: list[ValidationError] = []
    for error in errors:
        code = error.code
        if ":/source_host" in error.path or ":/source_host_installation_id" in error.path or ":/agent_" in error.path:
            code = "FR-003"
        elif ":/role_category" in error.path or ":/authority_context" in error.path or ":/mutation_classes" in error.path or ":/allowed_repositories" in error.path:
            code = "FR-005"
        elif any(f":/{field}" in error.path for field in STORAGE_FIELDS):
            code = "FR-004"
        normalized.append(
            ValidationError(code=code, path=error.path, message=error.message, contract=error.contract)
        )
    return normalized


def validate_identity_record(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors = _schema_errors(record, path)

    if record.get("human_ratifier_roles") == [] and not any("human_ratifier_roles" in error.path for error in errors):
        errors.append(
            make_error(
                "FR-001",
                path,
                "/human_ratifier_roles",
                "human_ratifier_roles must contain at least one human ratifier role",
                CONTRACT,
            )
        )

    repo_root = _repo_root_for(path)
    for field in STORAGE_FIELDS:
        value = record.get(field)
        if isinstance(value, str) and value.strip():
            storage_path = repo_root / value
            if not storage_path.is_dir():
                errors.append(
                    make_error(
                        "FR-004",
                        path,
                        f"/{field}",
                        f"declared storage directory does not exist: {value}",
                        CONTRACT,
                    )
                )

    return errors


@register(CHECK_NAME, ["FR-001", "FR-002", "FR-003", "FR-004", "FR-005"])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_identity_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error("FR-001", record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(make_error("FR-001", record_path, "/", "identity record must be a YAML mapping", CONTRACT))
            continue
        errors.extend(validate_identity_record(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
