"""Shared git helpers for local validator checks."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path


def run_git(args: Sequence[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command, returning (returncode, stdout, stderr). Never raises."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout, result.stderr


def repo_root_for(path: Path) -> Path:
    """Return the nearest repository-like root for ``path``."""
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists() or (candidate / "validators").is_dir():
            return candidate
    return Path.cwd()
