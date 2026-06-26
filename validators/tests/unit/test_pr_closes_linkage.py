"""Unit tests for the PR closes-linkage validator check."""

from __future__ import annotations

from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks import pr_closes_linkage as chk


def _write_manifest(root: Path, name: str, body: str) -> Path:
    manifest_dir = root / ".ce" / "pr-manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / name
    path.write_text(body, encoding="utf-8")
    return path


def test_check_is_registered():
    assert chk.CHECK_NAME in registered_checks()


def test_correct_closes_line_passes(tmp_path: Path):
    _write_manifest(tmp_path, "ce262-closes-linkage-guard.md", "Closes creator-engine/ce-ops#262\n")
    result = chk.run([tmp_path])
    assert result.ok, [err.format() for err in result.errors]
    assert result.warnings == ()


def test_missing_closes_line_warns_only(tmp_path: Path):
    _write_manifest(tmp_path, "ce262-closes-linkage-guard.md", "# manifest\n")
    result = chk.run([tmp_path])
    assert result.ok, [err.format() for err in result.errors]
    assert [warning.code for warning in result.warnings] == [chk.CODE_MISSING]


def test_wrong_closes_number_errors(tmp_path: Path):
    _write_manifest(tmp_path, "ce262-closes-linkage-guard.md", "Closes creator-engine/ce-ops#263\n")
    result = chk.run([tmp_path])
    assert not result.ok
    assert [error.code for error in result.errors] == [chk.CODE_MISMATCH]
    assert result.warnings == ()


def test_non_ticket_manifest_passes(tmp_path: Path):
    _write_manifest(tmp_path, "feature-branch.md", "Closes creator-engine/ce-ops#999\n")
    result = chk.run([tmp_path])
    assert result.ok, [err.format() for err in result.errors]
    assert result.warnings == ()


def test_empty_directory_passes(tmp_path: Path):
    (tmp_path / ".ce" / "pr-manifests").mkdir(parents=True)
    result = chk.run([tmp_path])
    assert result.ok, [err.format() for err in result.errors]
    assert result.warnings == ()
