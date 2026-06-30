from __future__ import annotations

import hashlib
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

from creator_engine_validator import ce_cli, main_head_install
from creator_engine_validator.main_head_install import (
    MainHeadInstallRefused,
    MainHeadVenvPromoter,
    build_main_head_artifact,
    clean_main_install,
    resolve_origin_main,
    verify_artifact_files,
)
from creator_engine_validator.wheel_bake import WheelManifest


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _write_main_repo(tmp_path: Path) -> tuple[Path, str]:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", "--initial-branch=main", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "checkout", "-q", "-b", "main")
    _git(work, "config", "user.email", "tests@example.invalid")
    _git(work, "config", "user.name", "CE Tests")

    package = work / "validators" / "creator_engine_validator"
    package.mkdir(parents=True)
    (work / "validators" / "pyproject.toml").write_text(
        """\
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "creator-engine-validator"
version = "0.3.0"
dependencies = []

[project.scripts]
ce = "creator_engine_validator.ce_cli:main"
cev3 = "creator_engine_validator.v3_cli:main"
""",
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "version.py").write_text('__version__ = "0.3.0"\n', encoding="utf-8")
    (package / "_version.py").write_text(
        'SEMVER = "0.3.0"\nBUILD_GIT_SHA = "' + ("0" * 40) + '"\n',
        encoding="utf-8",
    )
    wheelhouse = work / "validators" / "wheelhouse"
    wheelhouse.mkdir()
    dep = wheelhouse / "dep-1.0.0-py3-none-any.whl"
    dep.write_bytes(b"dependency wheel\n")

    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "main source")
    commit = _git(work, "rev-parse", "--verify", "HEAD")
    _git(work, "push", "-q", "-u", "origin", "main")
    _git(work, "fetch", "-q", "origin", "main")
    return work, commit


def _fake_builder(repo_root: Path, out_dir: Path, *, build_dir: Path | None = None) -> WheelManifest:
    del build_dir
    version = tomllib.loads((repo_root / "validators" / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    build_identity = (repo_root / "validators" / "creator_engine_validator" / "_version.py").read_text(
        encoding="utf-8"
    )
    source_commit = _git(repo_root, "rev-parse", "--verify", "HEAD")
    assert f'BUILD_GIT_SHA = "{source_commit}"' in build_identity
    wheel_name = f"creator_engine_validator-{version}-py3-none-any.whl"
    wheel = out_dir / wheel_name
    wheel.write_bytes(f"wheel\nversion={version}\nsource={source_commit}\n".encode("utf-8"))
    return WheelManifest(
        wheel_name=wheel_name,
        sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
        version=version,
        source_commit=source_commit,
    )


def test_resolve_and_build_main_head_artifact_hashes_source_and_wheel(tmp_path: Path):
    repo, commit = _write_main_repo(tmp_path)
    resolved = resolve_origin_main(repo)
    assert resolved.commit == commit
    assert re.fullmatch(r"[0-9a-f]{64}", resolved.git_source_sha256)

    artifact = build_main_head_artifact(
        resolved,
        work_root=tmp_path / "artifact-work",
        build_wheel=_fake_builder,
    )
    try:
        assert artifact.identity.commit == commit
        assert artifact.package_version == "0.3.0"
        assert artifact.wheel_sha256 == hashlib.sha256(artifact.wheel_path.read_bytes()).hexdigest()
        assert artifact.manifest()["trust_model"] == "verified-source-build-main-head"
        assert artifact.manifest()["signature"] == "none"
        assert verify_artifact_files(artifact)["ok"] is True
    finally:
        main_head_install._remove_worktree(resolved, artifact.worktree)


def test_build_refuses_when_builder_mutates_source_after_hash(tmp_path: Path):
    repo, _commit = _write_main_repo(tmp_path)
    resolved = resolve_origin_main(repo)

    def mutating_builder(repo_root: Path, out_dir: Path, *, build_dir: Path | None = None) -> WheelManifest:
        manifest = _fake_builder(repo_root, out_dir, build_dir=build_dir)
        (repo_root / "validators" / "creator_engine_validator" / "version.py").write_text(
            '__version__ = "tampered"\n',
            encoding="utf-8",
        )
        return manifest

    with pytest.raises(MainHeadInstallRefused, match="source changed during wheel build"):
        build_main_head_artifact(
            resolved,
            work_root=tmp_path / "artifact-work",
            build_wheel=mutating_builder,
        )


def test_promoter_refuses_before_install_when_wheel_hash_mismatches(tmp_path: Path):
    repo, _commit = _write_main_repo(tmp_path)
    resolved = resolve_origin_main(repo)
    artifact = build_main_head_artifact(
        resolved,
        work_root=tmp_path / "artifact-work",
        build_wheel=_fake_builder,
    )
    try:
        artifact.wheel_path.write_bytes(b"tampered wheel\n")
        with pytest.raises(MainHeadInstallRefused, match="artifact_hash_mismatch"):
            MainHeadVenvPromoter().apply(tmp_path / "install-root", artifact)
        assert not (tmp_path / "install-root" / "venv").exists()
    finally:
        main_head_install._remove_worktree(resolved, artifact.worktree)


def test_clean_main_install_uses_resolver_and_promoter_without_release_signature(tmp_path: Path):
    repo, commit = _write_main_repo(tmp_path)
    install_root = tmp_path / "install-root"
    seen: dict[str, str] = {}

    class FakePromoter:
        def apply(self, root: Path, artifact) -> tuple[str, ...]:
            verify_artifact_files(artifact)
            seen["commit"] = artifact.identity.commit
            seen["signature"] = artifact.manifest()["signature"]
            root.mkdir(parents=True)
            return ("fake_promote_verified_artifact",)

    result = clean_main_install(
        repo_root=repo,
        install_root=install_root,
        build_wheel=_fake_builder,
        promoter=FakePromoter(),
    )

    assert result.ok
    assert result.status == "installed"
    assert seen == {"commit": commit, "signature": "none"}
    assert "fake_promote_verified_artifact" in result.actions


def test_clean_main_install_cli_and_update_track_main_route_to_main_resolver(monkeypatch):
    calls: list[tuple[str, bool]] = []

    def fake_run_cli(args) -> int:
        calls.append((args.group, bool(getattr(args, "check", False))))
        return 0

    monkeypatch.setattr(ce_cli.main_head_install, "run_cli", fake_run_cli)

    assert ce_cli.main(["clean-main-install", "--check"]) == 0
    assert ce_cli.main(["update", "--track", "main", "--check"]) == 0

    assert calls == [("clean-main-install", True), ("update", True)]

