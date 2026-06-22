from __future__ import annotations

import configparser
import hashlib
import subprocess
import tomllib
import zipfile
from pathlib import Path

import pytest

from creator_engine_validator.version import __version__
from creator_engine_validator.wheel_bake import (
    WheelBakeError,
    build_app_wheel_from_source,
)


def _entry_points(wheel: Path) -> dict[str, str]:
    with zipfile.ZipFile(wheel) as zf:
        names = [name for name in zf.namelist() if name.endswith(".dist-info/entry_points.txt")]
        assert names, "built wheel has no entry_points.txt"
        raw = zf.read(names[0]).decode("utf-8")
    cp = configparser.ConfigParser()
    cp.read_string(raw)
    return dict(cp["console_scripts"]) if cp.has_section("console_scripts") else {}


def _source_scripts(repo_root: Path) -> dict[str, str]:
    data = tomllib.loads((repo_root / "validators" / "pyproject.toml").read_text(encoding="utf-8"))
    return dict(data["project"]["scripts"])


def _wheel_text(wheel: Path, rel: str) -> str:
    with zipfile.ZipFile(wheel) as zf:
        return zf.read(f"creator_engine_validator/{rel}").decode("utf-8")


def _console_surface(repo_root: Path, wheel: Path) -> tuple[dict[str, str], str, str]:
    scripts = _entry_points(wheel)
    return (
        {name: scripts[name] for name in ("ce", "cev3", "creator-engine-validator")},
        _wheel_text(wheel, "ce_cli.py"),
        _wheel_text(wheel, "v3_cli.py"),
    )


@pytest.mark.xdist_group("wheel-build")
def test_build_app_wheel_from_source_returns_recomputed_manifest(
    repo_root: Path, tmp_path: Path
):
    manifest = build_app_wheel_from_source(repo_root, tmp_path)
    wheel = tmp_path / manifest.wheel_name
    head = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert wheel.is_file()
    assert manifest.version == __version__
    assert manifest.sha256 == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert manifest.source_commit == head
    assert len(manifest.source_commit) == 40
    assert all(ch in "0123456789abcdef" for ch in manifest.source_commit)

    source_scripts = _source_scripts(repo_root)
    wheel_scripts = _entry_points(wheel)
    for script in ("ce", "cev3", "creator-engine-validator"):
        assert wheel_scripts[script] == source_scripts[script]
    assert _wheel_text(wheel, "ce_cli.py") == (
        repo_root / "validators" / "creator_engine_validator" / "ce_cli.py"
    ).read_text(encoding="utf-8")
    assert _wheel_text(wheel, "v3_cli.py") == (
        repo_root / "validators" / "creator_engine_validator" / "v3_cli.py"
    ).read_text(encoding="utf-8")


@pytest.mark.xdist_group("wheel-build")
def test_build_app_wheel_from_source_is_surface_deterministic(repo_root: Path, tmp_path: Path):
    left = tmp_path / "left"
    right = tmp_path / "right"

    left_manifest = build_app_wheel_from_source(repo_root, left)
    right_manifest = build_app_wheel_from_source(repo_root, right)
    left_wheel = left / left_manifest.wheel_name
    right_wheel = right / right_manifest.wheel_name

    assert left_manifest.version == right_manifest.version
    assert left_manifest.source_commit == right_manifest.source_commit
    assert left_manifest.sha256 == right_manifest.sha256
    assert left_wheel.read_bytes() == right_wheel.read_bytes()
    assert _console_surface(repo_root, left_wheel) == _console_surface(repo_root, right_wheel)
    assert not (repo_root / "validators" / "build").exists()
    assert not (repo_root / "validators" / "creator_engine_validator.egg-info").exists()


@pytest.mark.wheel_bake_gate
@pytest.mark.xdist_group("wheel-build")
def test_source_build_does_not_require_or_recreate_committed_app_wheel(
    repo_root: Path, tmp_path: Path
):
    manifest = build_app_wheel_from_source(repo_root, tmp_path)
    fresh = tmp_path / manifest.wheel_name
    committed = sorted((repo_root / "validators" / "wheelhouse").glob("creator_engine_validator-*.whl"))

    assert fresh.is_file()
    assert hashlib.sha256(fresh.read_bytes()).hexdigest() == manifest.sha256
    assert committed == []


def test_build_app_wheel_from_source_raises_typed_error_on_bad_repo(tmp_path: Path):
    with pytest.raises(WheelBakeError):
        build_app_wheel_from_source(tmp_path / "missing", tmp_path / "out")
