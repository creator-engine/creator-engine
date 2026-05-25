"""Gate 3 transcript archive runtime (`ce lane archive`; RV1-032).

Implements the archive/hash discipline from
``docs/operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md``: copy the transcript bytes
exactly into an instance-local archive root, compute the byte-level SHA256,
and emit the archive path + hash. The archive root MUST be git-ignored when it
lives inside a repository — otherwise the transcript body (which routinely
contains instance-local paths and pane identifiers) would leak into the
tracked tree. The transcript body itself is never written to a tracked file.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Sequence


class ArchiveError(Exception):
    """Base class for transcript archive errors."""


class TranscriptMissing(ArchiveError):
    """The transcript to archive does not exist."""


class ArchiveRootNotIgnored(ArchiveError):
    """The archive root is inside a repository but is not git-ignored."""


@dataclass(frozen=True)
class ArchiveResult:
    archive_path: Path
    sha256: str
    source: Path


GitRunner = Callable[[Sequence[str]], subprocess.CompletedProcess]


def _default_git_runner(argv: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(list(argv), check=False, capture_output=True, text=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _detect_repo_root(path: Path) -> Path | None:
    """Walk up from ``path`` looking for an enclosing git work tree."""
    try:
        current = path.resolve()
    except OSError:
        current = path
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _is_inside(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root.resolve())
    except (OSError, ValueError):
        return False


def _is_ignored(repo_root: Path, path: Path, runner: GitRunner) -> bool:
    proc = runner(["git", "-C", str(repo_root), "check-ignore", "-q", "--", str(path)])
    return proc.returncode == 0


def archive(
    *,
    transcript: Path | str,
    archive_root: Path | str,
    batch_slug: str,
    role: str,
    repo_root: Path | str | None = None,
    now: datetime | None = None,
    git_runner: GitRunner | None = None,
) -> ArchiveResult:
    """Archive ``transcript`` under ``archive_root`` and hash the bytes.

    Refuses before any write if the transcript is missing or if ``archive_root``
    lives inside a repository without being git-ignored.
    """
    transcript = Path(transcript)
    archive_root = Path(archive_root)
    runner = git_runner or _default_git_runner

    if not transcript.is_file():
        raise TranscriptMissing(f"transcript not found: {transcript}")

    enclosing = Path(repo_root) if repo_root is not None else _detect_repo_root(archive_root)
    if enclosing is not None and _is_inside(archive_root, enclosing):
        if not _is_ignored(enclosing, archive_root, runner):
            raise ArchiveRootNotIgnored(
                f"archive root {archive_root} is inside repo {enclosing} but is not git-ignored; "
                "transcript bodies must live under an ignored path"
            )

    ts = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    archive_root.mkdir(parents=True, exist_ok=True)
    target = archive_root / f"{ts}-{batch_slug}-{role}.txt"

    data = transcript.read_bytes()
    tmp = target.with_name(f"{target.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    tmp.write_bytes(data)
    tmp.rename(target)

    digest = sha256_bytes(target.read_bytes())
    return ArchiveResult(archive_path=target, sha256=digest, source=transcript)
