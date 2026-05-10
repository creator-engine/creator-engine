"""JSON Schema Draft 2020-12 validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .loader import load_yaml
from .reporting import ValidationError


def _json_pointer(error_path) -> str:
    parts = [str(part).replace("~", "~0").replace("/", "~1") for part in error_path]
    return "/" + "/".join(parts) if parts else "/"


def load_schema(schema_path: str | Path) -> dict[str, Any]:
    data = load_yaml(schema_path)
    if not isinstance(data, dict):
        raise ValueError(f"schema must be a mapping: {schema_path}")
    return data


def validate_with_schema(instance: Any, schema_path: str | Path, instance_path: str | Path, *, code: str, contract: str | Path) -> list[ValidationError]:
    """Validate an instance against a YAML-encoded Draft 2020-12 schema."""
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("jsonschema is required; install validators/requirements.txt") from exc

    schema = load_schema(schema_path)
    validator = Draft202012Validator(schema)
    errors: list[ValidationError] = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        pointer = _json_pointer(err.path)
        errors.append(
            ValidationError(
                code=code,
                path=f"{instance_path}:{pointer}",
                message=err.message,
                contract=str(contract),
            )
        )
    return errors
