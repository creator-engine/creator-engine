"""JSON Schema Draft 2020-12 validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .loader import load_yaml
from .reporting import ValidationError


def _json_pointer(error_path) -> str:
    parts = [str(part).replace("~", "~0").replace("/", "~1") for part in error_path]
    return "/" + "/".join(parts) if parts else "/"


#: Package/repo root. The package's own schema names are embedded as repo-root-relative
#: constants (e.g. ``SCHEMA = "schemas/install-answers.schema.yaml"``); this is the same
#: anchor ``ce_event_runtime.py`` / ``fanin_runtime.py`` use for their ``SCHEMA_PATH``s
#: (``schema.py`` -> parents[0]=package, parents[1]=``validators``, parents[2]=repo root).
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_SCHEMAS_DIR = _PACKAGE_ROOT / "schemas"


def _resolve_schema_path(schema_path: str | Path) -> Path:
    """Resolve a schema path for loading (ce-ops#54).

    A package schema referenced by a root-relative name (``schemas/…``) is anchored to
    the package root so the CLI loads it from ANY working directory, not only the repo
    root. Absolute paths, and genuinely cwd/user-relative paths that are NOT one of the
    package's own schemas — e.g. a user-supplied ``--answers-schema <relative>`` — are
    left untouched and keep their existing cwd-relative semantics. The distinguishing
    test is conservative: anchor only when the joined path is a file that resolves under
    the package ``schemas/`` directory; otherwise fall back to the path as given.
    """
    p = Path(schema_path)
    if p.is_absolute():
        return p
    anchored = _PACKAGE_ROOT / p
    try:
        within_package_schemas = anchored.resolve().is_relative_to(
            _PACKAGE_SCHEMAS_DIR.resolve()
        )
    except (OSError, ValueError):  # pragma: no cover - defensive
        within_package_schemas = False
    if within_package_schemas and anchored.is_file():
        return anchored
    return p


def load_schema(schema_path: str | Path) -> dict[str, Any]:
    data = load_yaml(_resolve_schema_path(schema_path))
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
