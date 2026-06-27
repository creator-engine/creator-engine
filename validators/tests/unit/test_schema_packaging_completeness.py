"""ce-ops#331 — schema packaging-completeness contract (fast unit invariants).

Regression guard for the release blocker where the installed wheel shipped ZERO
schema files, so every schema-validating CLI (``ce brain init`` and the rest)
crashed with ``No such file or directory: schemas/<name>.schema.yaml`` in any
real install outside a source checkout.

Root cause: ``schemas/`` lived at the repo root, one level ABOVE the
``validators/`` build root, with no ``package-data`` / force-include, so it was
physically outside the sdist/wheel tree and never packaged. It only ever
"worked" because tests/CI run from the source tree (CWD = repo root). The fix
relocates the schema files INTO the package at
``creator_engine_validator/schemas/`` (shipped via ``package-data``), with a
repo-root ``schemas`` symlink preserving repo-root-relative dev/CI tooling, and
makes ``schema._resolve_schema_path`` anchor to the packaged directory so
resolution is robust in both a source tree and an installed wheel.

These are the FAST invariants that make the wheel ship the schemas and the
resolver find them. The end-to-end build/install/run proof (the gap CI missed)
lives in ``tests/integration/test_schema_packaging_wheel.py`` (module-marked
slow per the test-tier split).
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

from creator_engine_validator import schema as schema_mod
from creator_engine_validator.schema import _resolve_schema_path

PACKAGE_ROOT = Path(schema_mod.__file__).resolve().parent
PACKAGE_SCHEMAS_DIR = PACKAGE_ROOT / "schemas"

#: Matches the ``schemas/<name>.schema.yaml`` string constants embedded throughout
#: the validator package (e.g. ``SCHEMA = "schemas/brain-assertion.schema.yaml"``).
_SCHEMA_CONST_RE = re.compile(r"schemas/[a-z0-9-]+\.schema\.yaml")


def _referenced_schema_paths() -> set[str]:
    """Every distinct ``schemas/*.schema.yaml`` literal in the package source."""
    refs: set[str] = set()
    for py in PACKAGE_ROOT.rglob("*.py"):
        refs.update(_SCHEMA_CONST_RE.findall(py.read_text(encoding="utf-8")))
    return refs


def test_in_package_schemas_dir_is_populated():
    """The schema YAML files are physically present inside the package."""
    assert PACKAGE_SCHEMAS_DIR.is_dir(), PACKAGE_SCHEMAS_DIR
    shipped = sorted(p.name for p in PACKAGE_SCHEMAS_DIR.glob("*.schema.yaml"))
    assert shipped, "no schema files found inside the package — the wheel will ship none"


def test_every_referenced_schema_constant_resolves_to_an_existing_file():
    """No ``schemas/*.schema.yaml`` constant resolves to a missing file.

    This is the resolver-level invariant behind ``ce brain init`` and friends:
    a constant that does not resolve is exactly the ``No such file or directory``
    crash from ce-ops#331.
    """
    refs = _referenced_schema_paths()
    assert refs, "expected schema constants in the package source"
    unresolved = sorted(rel for rel in refs if not _resolve_schema_path(rel).is_file())
    assert not unresolved, f"schema constants that do not resolve to a file: {unresolved}"


def test_resolver_anchors_into_the_packaged_schemas_dir():
    """Resolution of a package schema lands inside the packaged ``schemas/`` dir.

    Guards against a regression where the anchor drifts back to a repo-root-only
    location that does not exist in an installed wheel.
    """
    resolved = _resolve_schema_path("schemas/brain-assertion.schema.yaml").resolve()
    assert resolved.is_file()
    assert resolved.is_relative_to(PACKAGE_SCHEMAS_DIR.resolve()), resolved


def test_pyproject_declares_schema_package_data(repo_root: Path):
    """``pyproject.toml`` ships the schema files as package data.

    Without this declaration the relocated files would not be included in the
    wheel even though they live inside the package directory.
    """
    pyproject = repo_root / "validators" / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    package_data = (
        data.get("tool", {})
        .get("setuptools", {})
        .get("package-data", {})
        .get("creator_engine_validator", [])
    )
    assert any(
        "schemas/" in pattern and pattern.endswith(".schema.yaml")
        for pattern in package_data
    ), f"pyproject must declare schemas/*.schema.yaml package-data, got {package_data!r}"
