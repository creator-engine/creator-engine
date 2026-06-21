"""Small helpers for recognizing enclosing git worktree roots."""
from __future__ import annotations

from pathlib import Path


def is_git_worktree_root(path: Path | str) -> bool:
    """Return true when ``path`` looks like a real git worktree root.

    An empty ``.git`` directory is not enough: pytest temp trees can live under
    ambient scratch roots that contain such a marker. A normal checkout carries
    ``.git/HEAD``; a secondary worktree carries a ``.git`` file pointing at a
    gitdir with ``HEAD``.
    """
    root = Path(path)
    dot_git = root / ".git"
    if dot_git.is_dir():
        return (dot_git / "HEAD").is_file()
    if not dot_git.is_file():
        return False
    try:
        first_line = dot_git.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return False
    prefix = "gitdir:"
    if not first_line.startswith(prefix):
        return False
    gitdir = Path(first_line[len(prefix):].strip())
    if not gitdir.is_absolute():
        gitdir = root / gitdir
    return (gitdir / "HEAD").is_file()


def find_enclosing_git_worktree(path: Path | str) -> Path | None:
    """Walk up from ``path`` and return the first real enclosing git worktree."""
    try:
        current = Path(path).resolve()
    except OSError:
        current = Path(path)
    for candidate in (current, *current.parents):
        if is_git_worktree_root(candidate):
            return candidate
    return None
