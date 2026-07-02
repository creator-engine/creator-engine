"""Commit-mode tests for release-bump."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from creator_engine_validator import cli
from creator_engine_validator.release_bump import ReleaseBumpError, commit_release_bump

import pytest


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _write_version_sources(root: Path, version: str = "0.2.0") -> None:
    package = root / "validators" / "creator_engine_validator"
    package.mkdir(parents=True, exist_ok=True)
    (root / "validators" / "pyproject.toml").write_text(
        f'[project]\nname = "creator-engine-validator"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (package / "version.py").write_text(
        f'"""version module."""\n\n__version__ = "{version}"\n',
        encoding="utf-8",
    )


def _init_repo(root: Path, version: str = "0.2.0") -> None:
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t.invalid")
    _git(root, "config", "user.name", "T")
    _write_version_sources(root, version)
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "initial version")


def test_commit_mode_refuses_dirty_tree(tmp_path: Path):
    root = tmp_path / "repo"
    _init_repo(root)
    (root / "dirty.txt").write_text("untracked\n", encoding="utf-8")

    with pytest.raises(ReleaseBumpError, match="dirty working tree"):
        commit_release_bump(repo_root=root, tag="release/v0.3.0", out_branch="release-bump-0-3-0")

    assert _git(root, "branch", "--show-current") in {"main", "master"}
    assert '__version__ = "0.2.0"' in (
        root / "validators" / "creator_engine_validator" / "version.py"
    ).read_text(encoding="utf-8")


def test_commit_mode_creates_deterministic_branch_message_and_carrier(tmp_path: Path):
    root = tmp_path / "repo"
    _init_repo(root)

    result = commit_release_bump(
        repo_root=root,
        tag="release/v0.3.0",
        out_branch="release-bump-0-3-0",
        carrier_date="2026-07-02",
    )

    assert result.branch == "release-bump-0-3-0"
    assert _git(root, "branch", "--show-current") == "release-bump-0-3-0"
    assert result.commit_message == "release-bump: 0.2.0 -> 0.3.0"
    assert _git(root, "log", "-1", "--pretty=%s") == "release-bump: 0.2.0 -> 0.3.0"
    assert tuple(
        sorted(_git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines())
    ) == (
        "validators/creator_engine_validator/version.py",
        "validators/pyproject.toml",
    )

    expected_paths = (
        ".ce/changelog/release-bump-0-3-0.md",
        ".ce/pr-manifests/release-bump-0-3-0.md",
        "validators/creator_engine_validator/version.py",
        "validators/pyproject.toml",
    )
    assert result.carriers.paths == expected_paths
    assert result.carriers.changelog_path.is_file()
    assert result.carriers.manifest_path.is_file()
    assert "2026-07-02" in result.carriers.changelog_path.read_text(encoding="utf-8")


def test_release_bump_commit_cli_json_output(tmp_path: Path, capsys):
    root = tmp_path / "repo"
    _init_repo(root)

    assert (
        cli.main(
            [
                "--json",
                "release-bump",
                "--repo-root",
                str(root),
                "--tag",
                "release/v0.3.0",
                "--commit",
                "--out-branch",
                "release-bump-0-3-0",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == "0.3.0"
    assert payload["branch"] == "release-bump-0-3-0"
    assert payload["commit_message"] == "release-bump: 0.2.0 -> 0.3.0"
    assert payload["carrier_paths"] == [
        ".ce/changelog/release-bump-0-3-0.md",
        ".ce/pr-manifests/release-bump-0-3-0.md",
        "validators/creator_engine_validator/version.py",
        "validators/pyproject.toml",
    ]


def test_commit_mode_has_no_network_side_effect(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    _init_repo(root)

    import creator_engine_validator.release_bump as rb

    real_git = rb._git
    commands: list[tuple[str, ...]] = []

    def recording_git(repo_root: Path, *args: str):
        commands.append(args)
        return real_git(repo_root, *args)

    monkeypatch.setattr(rb, "_git", recording_git)

    commit_release_bump(
        repo_root=root,
        tag="release/v0.3.0",
        out_branch="release-bump-0-3-0",
        carrier_date="2026-07-02",
    )

    disallowed = {"fetch", "push", "pull", "ls-remote", "request-pull", "remote"}
    assert not any(command and command[0] in disallowed for command in commands)
