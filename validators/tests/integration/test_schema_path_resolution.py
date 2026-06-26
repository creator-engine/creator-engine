"""ce-ops#54 — package schemas resolve from ANY working directory.

The bug: the package's own schema names are repo-root-relative constants (e.g.
``SCHEMA = "schemas/state-version-record.schema.yaml"``), and ``load_schema`` opened
them cwd-relative — so a check invoked from anywhere other than the repo root raised
``LoaderError`` trying to read its own schema. ``load_schema`` now anchors the package's
own schema names to the package root regardless of cwd.

These integration tests drive a real registered check's ``run()`` + ``load_schema``
itself from an arbitrary cwd that is NOT the repo root, and prove the schema still loads.
The cwd deliberately has no ``schemas/`` tree, so a pass can ONLY come from anchoring.

Scope note: this fix centralizes PACKAGE-SCHEMA resolution in ``load_schema``. Other,
unrelated cwd-relative contract loads (e.g. the ``mutation_class`` taxonomy ``.yml``) are
NOT in ce-ops#54's scope, so we drive a single schema-only check here rather than the
full ``ce check`` umbrella (which fans out to those out-of-scope loads).
"""
from __future__ import annotations

import contextlib
from pathlib import Path

import pytest

from creator_engine_validator.checks import state_version_record
from creator_engine_validator.loader import LoaderError
from creator_engine_validator.schema import load_schema
pytestmark = pytest.mark.slow


# A well-formed example whose check loads ONLY a RELATIVE package-schema constant
# (``checks/state_version_record.py`` → ``SCHEMA = "schemas/state-version-record.schema.yaml"``)
# plus the (absolute) record path — no other cwd-relative input.
_WELL_FORMED = ("examples", "well-formed", "state-version-record", "current.yaml")
_PACKAGE_SCHEMA = "schemas/state-version-record.schema.yaml"


def test_registered_check_loads_package_schema_from_arbitrary_cwd(repo_root: Path, tmp_path: Path):
    example = repo_root.joinpath(*_WELL_FORMED)
    assert example.is_file()
    # the arbitrary cwd genuinely lacks a schemas/ tree → success proves anchoring
    assert not (tmp_path / "schemas").exists()
    with contextlib.chdir(tmp_path):
        result = state_version_record.run([example])
    # the check loaded its package schema from outside the repo root and the
    # well-formed record validated clean (pre-fix this raised LoaderError on the schema)
    assert result.ok, [e.message for e in result.errors]


def test_load_schema_from_arbitrary_cwd_returns_package_schema(repo_root: Path, tmp_path: Path):
    # the schema is NOT reachable cwd-relative from here (the pre-fix failure mode)…
    assert not (tmp_path / _PACKAGE_SCHEMA).exists()
    with contextlib.chdir(tmp_path):
        loaded = load_schema(_PACKAGE_SCHEMA)
    # …yet it loads: the loader anchored the package schema to the package root
    assert isinstance(loaded, dict) and loaded.get("$schema")
    assert (repo_root / _PACKAGE_SCHEMA).is_file()


def test_user_relative_schema_stays_cwd_relative_from_arbitrary_cwd(tmp_path: Path):
    """Edge case: a relative path that is NOT a package schema (a user-supplied schema)
    is loaded cwd-relative — it is neither anchored to the package root nor masked by a
    package schema of a different name."""
    local = tmp_path / "user.schema.yaml"
    local.write_text("$schema: x\nrequired: []\n", encoding="utf-8")
    with contextlib.chdir(tmp_path):
        assert load_schema("user.schema.yaml") == {"$schema": "x", "required": []}
        # a relative name with no package or cwd file still fails closed (no silent empty)
        with pytest.raises(LoaderError):
            load_schema("user-missing.schema.yaml")
