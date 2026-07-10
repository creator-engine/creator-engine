"""Resolve validator Python for linked worktrees.

Creator Engine seats commonly run in per-unit Git worktrees, but the validator
virtualenv belongs to the main checkout. Worktrees intentionally share the main
repo's ``.venv`` by absolute path instead of copying or rebuilding a venv per
worktree: duplicate worktree venvs have burned tens of gigabytes of disk during
contained-seat incidents, so the safe default is share, don't duplicate.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

CE_VALIDATOR_PYTHON_ENV = "CE_VALIDATOR_PYTHON"
REPAIR_COMMAND = ".venv/bin/python -m pip install -e validators"


class CommandResultLike(Protocol):
    returncode: int
    stdout: str
    stderr: str


class GitRunner(Protocol):
    def __call__(self, argv: Sequence[str], cwd: Path) -> CommandResultLike: ...


class WorktreePythonError(RuntimeError):
    """Raised when no fail-closed shared validator Python can be resolved."""


def _default_git_runner(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _resolve_git_path(repo_root: Path, raw_path: str) -> Path:
    path = Path(raw_path.strip())
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _git_rev_parse_path(worktree_root: Path, flag: str, runner: GitRunner) -> Path:
    result = runner(["git", "rev-parse", flag], worktree_root)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"git rev-parse {flag} failed"
        raise WorktreePythonError(detail)
    return _resolve_git_path(worktree_root, result.stdout)


def is_linked_worktree(worktree_root: str | Path, runner: GitRunner | None = None) -> bool:
    """Return true when ``worktree_root`` has a Git dir distinct from its common dir."""
    root = Path(worktree_root).resolve()
    run = runner or _default_git_runner
    return _git_rev_parse_path(root, "--git-common-dir", run) != _git_rev_parse_path(root, "--git-dir", run)


def main_repo_root_from_common_dir(common_dir: str | Path) -> Path:
    """Infer the main checkout root from a non-bare common Git directory."""
    common = Path(common_dir).resolve()
    if common.name == ".git":
        return common.parent
    return common


def resolve_worktree_python(
    worktree_root: str | Path,
    main_repo_root: str | Path,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    """Resolve the Python for a worktree, preserving explicit env precedence."""
    environ = os.environ if env is None else env
    explicit = environ.get(CE_VALIDATOR_PYTHON_ENV)
    if explicit:
        return explicit
    return ensure_worktree_python(worktree_root, main_repo_root)


def ensure_worktree_python(worktree_root: str | Path, main_repo_root: str | Path) -> str:
    """Return the main repo venv Python if it imports the validator package."""
    worktree = Path(worktree_root).resolve()
    main_repo = Path(main_repo_root).resolve()
    candidate = main_repo / ".venv" / "bin" / "python"

    if candidate.is_file():
        result = subprocess.run(
            [str(candidate), "-c", "import creator_engine_validator"],
            cwd=worktree,
            env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return str(candidate)
        detail = (result.stderr or result.stdout).strip()
    else:
        detail = f"{candidate} does not exist"

    raise WorktreePythonError(
        "No usable shared Creator Engine validator Python found for linked worktree "
        f"{worktree}. Checked {candidate}. {detail}. Repair from the main repo by running: "
        f"{REPAIR_COMMAND}"
    )
