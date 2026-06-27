"""JSON Schema Draft 2020-12 validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .loader import load_yaml
from .reporting import ValidationError


def _json_pointer(error_path) -> str:
    parts = [str(part).replace("~", "~0").replace("/", "~1") for part in error_path]
    return "/" + "/".join(parts) if parts else "/"


#: The package's own schema names are embedded as ``schemas/…`` constants (e.g.
#: ``SCHEMA = "schemas/install-answers.schema.yaml"``) throughout the codebase; the
#: same anchor ``ce_event_runtime.py`` / ``fanin_runtime.py`` use for their
#: ``SCHEMA_PATH``s. The schema files are PACKAGED data shipped INSIDE the wheel at
#: ``creator_engine_validator/schemas/`` (ce-ops#331) — they previously lived only at
#: the repo root (``parents[2]``), one level ABOVE the ``validators/`` build root, so
#: they were never included in the sdist/wheel and every schema-validating CLI crashed
#: in an installed (non-source-checkout) environment. Anchoring to the package
#: directory makes resolution robust in BOTH an installed wheel and a source tree (a
#: repo-root ``schemas`` symlink keeps repo-root-relative dev/CI tooling working).
#:
#: Resolution prefers the in-package ``schemas/`` directory. A repo-root fallback is
#: retained so a stale install whose schemas were not yet repackaged, or a source-tree
#: layout discovered via ``parents[2]``, still resolves rather than hard-failing.
_PACKAGE_DIR = Path(__file__).resolve().parent
_PACKAGE_SCHEMAS_DIR = _PACKAGE_DIR / "schemas"
#: Legacy repo-root anchor (``schema.py`` -> parents[0]=package, parents[1]=``validators``,
#: parents[2]=repo root). Retained only as a defensive fallback for source-tree layouts.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_schema_path(schema_path: str | Path) -> Path:
    """Resolve a schema path for loading (ce-ops#54, ce-ops#331).

    A package schema referenced by a root-relative name (``schemas/…``) is anchored to
    the PACKAGED schemas directory so the CLI loads it from ANY working directory and
    from an installed wheel, not only a source-tree repo root. Absolute paths, and
    genuinely cwd/user-relative paths that are NOT one of the package's own schemas —
    e.g. a user-supplied ``--answers-schema <relative>`` — are left untouched and keep
    their existing cwd-relative semantics. The distinguishing test is conservative:
    anchor only when the joined path is a file that resolves under a ``schemas/``
    directory the package owns; otherwise fall back to the path as given.

    ``schemas/X`` is the canonical reference, so the joined relative path is checked
    against the in-package directory first and, defensively, the repo-root anchor.
    """
    p = Path(schema_path)
    if p.is_absolute():
        return p
    for schemas_dir, anchor in (
        # In-package data (the wheel ships these); strip the leading ``schemas/``
        # segment when present so ``schemas/X`` maps onto ``<pkg>/schemas/X``.
        (_PACKAGE_SCHEMAS_DIR, _PACKAGE_DIR),
        # Defensive source-tree fallback: repo-root ``schemas/X``.
        (_PACKAGE_SCHEMAS_DIR, _REPO_ROOT),
    ):
        anchored = anchor / p
        try:
            within = anchored.resolve().is_relative_to(schemas_dir.resolve())
        except (OSError, ValueError):  # pragma: no cover - defensive
            within = False
        if within and anchored.is_file():
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
