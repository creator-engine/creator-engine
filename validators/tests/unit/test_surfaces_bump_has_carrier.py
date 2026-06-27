"""Unit tests for the surface-bump carrier gate."""

from __future__ import annotations

from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import surfaces_manifest as chk


def _write_repo(root: Path) -> Path:
    manifest = root / chk.MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text("surfaces: []\n", encoding="utf-8")
    (root / "validators" / "creator_engine_validator" / "checks").mkdir(parents=True)
    return manifest


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_surfaces_bump_has_carrier_is_registered():
    assert chk.CARRIER_CHECK_NAME in registered_checks()


def test_manifest_path_without_carrier_fails(tmp_path: Path):
    manifest = _write_repo(tmp_path)

    result = chk.run_carrier([manifest])

    assert chk.CODE_BUMP_MISSING_CARRIER in _codes(result)


def test_manifest_path_with_carrier_passes(tmp_path: Path):
    manifest = _write_repo(tmp_path)
    carrier = tmp_path / chk.CARRIERS_DIR / "surface-bump-codex-0.142.0.md"
    carrier.parent.mkdir()
    carrier.write_text("---\nsurface: codex\n---\n", encoding="utf-8")

    result = chk.run_carrier([manifest])

    assert result.ok, [error.format() for error in result.errors]


def test_non_manifest_path_passes(tmp_path: Path):
    _write_repo(tmp_path)
    path = tmp_path / "validators" / "example.py"
    path.write_text("VALUE = 1\n", encoding="utf-8")

    result = chk.run_carrier([path])

    assert result.ok, [error.format() for error in result.errors]
