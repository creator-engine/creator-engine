import contextlib
from pathlib import Path

import pytest

from creator_engine_validator import schema as schema_mod
from creator_engine_validator.schema import load_schema, validate_with_schema


def test_validate_with_schema_reports_json_pointer(tmp_path: Path):
    schema = tmp_path / "schema.yaml"
    schema.write_text("""
$schema: https://json-schema.org/draft/2020-12/schema
required: [name]
properties:
  name:
    type: string
""".lstrip())

    errors = validate_with_schema({}, schema, "example.yml", code="FR-X", contract="docs/contracts/example.md")

    assert len(errors) == 1
    assert errors[0].code == "FR-X"
    assert errors[0].path == "example.yml:/"
    assert errors[0].contract == "docs/contracts/example.md"


# ---------------------------------------------------------------------------
# ce-ops#54 — package schema names resolve from ANY cwd (not just the repo root)
# ---------------------------------------------------------------------------

#: A package schema referenced by its repo-root-relative constant value.
_PACKAGE_SCHEMA_NAME = "schemas/install-answers.schema.yaml"


def test_load_schema_anchors_package_schema_from_arbitrary_cwd(tmp_path: Path):
    """The bug (ce-ops#54): a package schema name like ``schemas/…`` resolved cwd-relative,
    so any ``ce`` invocation outside the repo root failed to load it. ``load_schema`` now
    anchors the package's own schema names to the package root regardless of cwd."""
    with contextlib.chdir(tmp_path):  # an arbitrary cwd that is NOT the repo root
        loaded = load_schema(_PACKAGE_SCHEMA_NAME)
    assert isinstance(loaded, dict) and loaded  # the real package schema, loaded
    assert loaded.get("$schema", "").startswith("https://json-schema.org/")


def test_load_schema_resolves_to_anchored_path(tmp_path: Path):
    """The resolver maps a package schema name onto the package's own ``schemas/`` file —
    an absolute path under the package root — not a cwd-relative one."""
    resolved = schema_mod._resolve_schema_path(_PACKAGE_SCHEMA_NAME)
    assert resolved.is_absolute() and resolved.is_file()
    assert resolved == schema_mod._PACKAGE_SCHEMAS_DIR / "install-answers.schema.yaml"


def test_resolve_schema_path_leaves_absolute_paths_untouched(tmp_path: Path):
    """An absolute schema path (the established ``parents[2] / 'schemas' / …`` constants)
    is returned unchanged."""
    abs_path = tmp_path / "custom.schema.yaml"
    abs_path.write_text("$schema: x\n", encoding="utf-8")
    assert schema_mod._resolve_schema_path(abs_path) == abs_path


def test_resolve_schema_path_keeps_user_relative_path_cwd_relative(tmp_path: Path):
    """Edge case: a user-supplied RELATIVE path that is NOT one of the package's own
    schemas (e.g. a ``--answers-schema my.yaml``) stays cwd-relative — it must not be
    silently re-anchored to the package root."""
    local = tmp_path / "my-answers.schema.yaml"
    local.write_text("$schema: x\nrequired: []\n", encoding="utf-8")
    with contextlib.chdir(tmp_path):
        # the cwd-relative name is preserved (not anchored under the package root)
        resolved = schema_mod._resolve_schema_path("my-answers.schema.yaml")
        assert resolved == Path("my-answers.schema.yaml")
        # and it still loads from the cwd
        loaded = load_schema("my-answers.schema.yaml")
    assert loaded == {"$schema": "x", "required": []}


def test_load_schema_missing_relative_still_errors(tmp_path: Path):
    """A relative name that matches no package schema and no cwd file still fails (the
    fallback keeps the pre-existing fail-closed behavior, not a silent empty schema)."""
    from creator_engine_validator.loader import LoaderError

    with contextlib.chdir(tmp_path):
        with pytest.raises(LoaderError):
            load_schema("schemas/does-not-exist.schema.yaml")
