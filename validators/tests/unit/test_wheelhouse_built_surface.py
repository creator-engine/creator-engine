"""Gate 9 — final-packaging contract: the tracked wheelhouse ``creator_engine_validator``
wheel must be built from the *current* source command surface.

The Option B packaging-contract tests (``test_packaging_contract.py``) assert the
pyproject pins, the cp314-only wheelhouse, and the uv.lock/requirements lockstep,
but nothing asserted that the *built* ``creator-engine-validator`` wheel shipped in
``validators/wheelhouse/`` actually reflects the current source. Gate 8 evidence
caught a G6-era wheel that still installed cleanly while missing the G7 ``ce fanin``
and G8 ``ce queue`` command groups.

These tests close that gap by introspecting the tracked wheel directly (stdlib
``zipfile`` only) and asserting:

* exactly one ``creator_engine_validator-*.whl`` is present,
* it bundles ``creator_engine_validator/ce_cli.py`` byte-for-byte identical to the
  current source (the wheel is not stale relative to source),
* the bundled ``ce`` surface registers ``fanin`` and ``queue`` and does **not**
  register a ``dev`` group, and
* the wheel's ``entry_points`` keep both console scripts and never expose ``dev``.
"""
from __future__ import annotations

import configparser
import zipfile
from pathlib import Path

import pytest

DISTRIBUTION = "creator_engine_validator"


@pytest.fixture()
def wheelhouse(repo_root: Path) -> Path:
    return repo_root / "validators" / "wheelhouse"


@pytest.fixture()
def validator_wheel(wheelhouse: Path) -> Path:
    matches = sorted(wheelhouse.glob(f"{DISTRIBUTION}-*.whl"))
    assert matches, f"no {DISTRIBUTION} wheel in {wheelhouse}"
    assert len(matches) == 1, f"expected exactly one {DISTRIBUTION} wheel, found {matches}"
    return matches[0]


def _bundled_ce_cli(wheel: Path) -> str:
    with zipfile.ZipFile(wheel) as zf:
        return zf.read(f"{DISTRIBUTION}/ce_cli.py").decode("utf-8")


def _entry_points(wheel: Path) -> dict[str, str]:
    with zipfile.ZipFile(wheel) as zf:
        names = [n for n in zf.namelist() if n.endswith(".dist-info/entry_points.txt")]
        assert names, "wheel has no entry_points.txt"
        raw = zf.read(names[0]).decode("utf-8")
    cp = configparser.ConfigParser()
    cp.read_string(raw)
    return dict(cp["console_scripts"]) if cp.has_section("console_scripts") else {}


def test_wheelhouse_validator_wheel_matches_current_source(
    validator_wheel: Path, repo_root: Path
):
    """The bundled ce surface must equal the current source — proves the wheel is rebuilt."""
    source = (repo_root / "validators" / DISTRIBUTION / "ce_cli.py").read_text(encoding="utf-8")
    bundled = _bundled_ce_cli(validator_wheel)
    assert bundled == source, (
        "tracked wheel's ce_cli.py is stale relative to source; rebuild the wheel "
        f"into {validator_wheel.parent}"
    )


def test_wheelhouse_validator_wheel_exposes_fanin_and_queue(validator_wheel: Path):
    bundled = _bundled_ce_cli(validator_wheel)
    assert 'add_parser(\n        "fanin"' in bundled or 'add_parser("fanin"' in bundled, (
        "built wheel does not register the `ce fanin` group (G7 surface missing)"
    )
    assert 'add_parser(\n        "queue"' in bundled or 'add_parser("queue"' in bundled, (
        "built wheel does not register the `ce queue` group (G8 surface missing)"
    )


def test_wheelhouse_validator_wheel_does_not_register_dev(validator_wheel: Path):
    bundled = _bundled_ce_cli(validator_wheel)
    assert 'add_parser("dev"' not in bundled and "add_parser('dev'" not in bundled, (
        "built wheel registers a `ce dev` group; v1.0 must not expose `ce dev`"
    )


def test_wheelhouse_validator_wheel_keeps_both_console_scripts_without_dev(
    validator_wheel: Path,
):
    scripts = _entry_points(validator_wheel)
    assert scripts.get("ce") == "creator_engine_validator.ce_cli:main"
    assert (
        scripts.get("creator-engine-validator") == "creator_engine_validator.cli:main"
    )
    assert "dev" not in scripts, f"unexpected `dev` console script: {scripts}"


# ---------------------------------------------------------------------------
# ce-ops#25: the wheel must ship the cev3 console script + the generated
# build-identity module, and bake the merge-parent SHA.
# ---------------------------------------------------------------------------


def test_wheelhouse_validator_wheel_exposes_cev3_console_script(validator_wheel: Path):
    scripts = _entry_points(validator_wheel)
    assert scripts.get("cev3") == "creator_engine_validator.v3_cli:main", (
        "built wheel does not ship the `cev3` console script (G-7 v3 entry point)"
    )


def test_wheelhouse_validator_wheel_bundles_generated_version(
    validator_wheel: Path, repo_root: Path
):
    """The wheel must bundle the generated _version.py byte-identical to source."""
    rel = f"{DISTRIBUTION}/_version.py"
    with zipfile.ZipFile(validator_wheel) as zf:
        assert rel in zf.namelist(), f"wheel does not bundle {rel}"
        bundled = zf.read(rel).decode("utf-8")
    source = (repo_root / "validators" / DISTRIBUTION / "_version.py").read_text(encoding="utf-8")
    assert bundled == source, "bundled _version.py is stale relative to source; rebuild the wheel"
    assert 'BUILD_GIT_SHA = "' in bundled, "bundled _version.py carries no baked BUILD_GIT_SHA"


def test_wheelhouse_bundled_version_surface_matches_source(
    validator_wheel: Path, repo_root: Path
):
    """version.py (the ce_version API) must be wheel-bundled byte-for-byte from source."""
    rel = f"{DISTRIBUTION}/version.py"
    with zipfile.ZipFile(validator_wheel) as zf:
        bundled = zf.read(rel).decode("utf-8")
    source = (repo_root / "validators" / DISTRIBUTION / "version.py").read_text(encoding="utf-8")
    assert bundled == source
    assert "def ce_version" in bundled, "built wheel's version.py lacks the ce_version API"
