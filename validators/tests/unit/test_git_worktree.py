"""Regression coverage for robust git worktree root detection."""
from __future__ import annotations

from pathlib import Path

from creator_engine_validator.git_worktree import (
    find_enclosing_git_worktree,
    is_git_worktree_root,
)


def test_empty_ancestor_dot_git_is_not_repo_root(tmp_path: Path):
    ambient = tmp_path / "ambient"
    scratch = ambient / "pytest-run" / "case"
    (ambient / ".git").mkdir(parents=True)
    scratch.mkdir(parents=True)

    assert not is_git_worktree_root(ambient)
    assert find_enclosing_git_worktree(scratch) is None


def test_git_dir_with_head_is_repo_root(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    assert is_git_worktree_root(repo)
    assert find_enclosing_git_worktree(repo / "nested") == repo


def test_git_worktree_file_with_head_is_repo_root(tmp_path: Path):
    repo = tmp_path / "repo"
    gitdir = tmp_path / "main" / ".git" / "worktrees" / "repo"
    repo.mkdir()
    gitdir.mkdir(parents=True)
    (repo / ".git").write_text("gitdir: ../main/.git/worktrees/repo\n", encoding="utf-8")
    (gitdir / "HEAD").write_text("ref: refs/heads/topic\n", encoding="utf-8")

    assert is_git_worktree_root(repo)
    assert find_enclosing_git_worktree(repo / "a" / "b") == repo
