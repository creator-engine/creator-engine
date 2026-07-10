from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from creator_engine_validator import worktree_venv


@dataclass(frozen=True)
class FakeResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def _fake_python(path: Path, *, returncode: int = 0, stderr: str = "") -> None:
    path.parent.mkdir(parents=True)
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-c\" ] && [ \"$2\" = \"import creator_engine_validator\" ]; then\n"
        f"  printf '%s' {stderr!r} >&2\n"
        f"  exit {returncode}\n"
        "fi\n"
        "exit 99\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)


def test_ensure_worktree_python_returns_shared_main_venv_python(tmp_path: Path):
    worktree = tmp_path / "worktree"
    main_repo = tmp_path / "main"
    worktree.mkdir()
    candidate = main_repo / ".venv" / "bin" / "python"
    _fake_python(candidate)

    resolved = worktree_venv.ensure_worktree_python(worktree, main_repo)

    assert resolved == str(candidate.resolve())


def test_is_linked_worktree_compares_git_common_dir_and_git_dir(tmp_path: Path):
    worktree = tmp_path / "worktree"
    main_repo = tmp_path / "main"
    worktree.mkdir()

    def runner(argv, cwd):
        assert cwd == worktree.resolve()
        if argv == ["git", "rev-parse", "--git-common-dir"]:
            return FakeResult(0, str(main_repo / ".git") + "\n")
        if argv == ["git", "rev-parse", "--git-dir"]:
            return FakeResult(0, str(main_repo / ".git" / "worktrees" / "worktree") + "\n")
        raise AssertionError(argv)

    assert worktree_venv.is_linked_worktree(worktree, runner)


def test_resolve_worktree_python_preserves_env_override_precedence(tmp_path: Path):
    explicit = "/opt/ce/bin/python"

    resolved = worktree_venv.resolve_worktree_python(
        tmp_path / "missing-worktree",
        tmp_path / "missing-main",
        env={worktree_venv.CE_VALIDATOR_PYTHON_ENV: explicit},
    )

    assert resolved == explicit


def test_ensure_worktree_python_fails_closed_with_repair_command(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "host-path"))
    worktree = tmp_path / "worktree"
    main_repo = tmp_path / "main"
    worktree.mkdir()
    candidate = main_repo / ".venv" / "bin" / "python"
    _fake_python(candidate, returncode=3, stderr="missing validator")

    with pytest.raises(worktree_venv.WorktreePythonError) as exc_info:
        worktree_venv.ensure_worktree_python(worktree, main_repo)

    message = str(exc_info.value)
    assert str(candidate.resolve()) in message
    assert worktree_venv.REPAIR_COMMAND in message
    assert "missing validator" in message
