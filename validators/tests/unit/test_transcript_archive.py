"""Unit tests for ``ce lane archive`` transcript hashing (RV1-032).

Implements the archive/hash discipline from
``docs/operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md``: copy bytes exactly,
compute a byte-level SHA256, and refuse a non-ignored archive root inside a
git repository.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import transcript_archive


def _git(args, cwd: Path):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    _git(["config", "user.email", "t@example.com"], repo)
    _git(["config", "user.name", "T"], repo)
    (repo / ".gitignore").write_text(".hermes/\n", encoding="utf-8")
    _git(["add", ".gitignore"], repo)
    _git(["commit", "-m", "init"], repo)
    return repo


def test_archive_hashes_transcript_bytes(tmp_path):
    transcript = tmp_path / "pane.txt"
    body = b"tool calls and authored content\nstop line\n"
    transcript.write_bytes(body)
    archive_root = tmp_path / "out"  # outside any git repo -> allowed

    result = transcript_archive.archive(
        transcript=transcript,
        archive_root=archive_root,
        batch_slug="gate3",
        role="implementer",
    )
    expected = hashlib.sha256(body).hexdigest()
    assert result.sha256 == expected
    assert result.archive_path.is_file()
    # copied byte-for-byte
    assert result.archive_path.read_bytes() == body
    # recomputing on disk matches the emitted hash
    assert hashlib.sha256(result.archive_path.read_bytes()).hexdigest() == expected


def test_archive_filename_carries_slug_and_role(tmp_path):
    transcript = tmp_path / "pane.txt"
    transcript.write_bytes(b"x")
    result = transcript_archive.archive(
        transcript=transcript,
        archive_root=tmp_path / "out",
        batch_slug="gate3-slug",
        role="reviewer",
    )
    assert "gate3-slug" in result.archive_path.name
    assert "reviewer" in result.archive_path.name


def test_archive_refuses_missing_transcript(tmp_path):
    with pytest.raises(transcript_archive.TranscriptMissing):
        transcript_archive.archive(
            transcript=tmp_path / "nope.txt",
            archive_root=tmp_path / "out",
            batch_slug="gate3",
            role="implementer",
        )


def test_archive_allows_ignored_root_inside_repo(git_repo):
    transcript = git_repo.parent / "pane.txt"
    transcript.write_bytes(b"hello\n")
    archive_root = git_repo / ".hermes" / "transcripts"  # ignored by .gitignore
    result = transcript_archive.archive(
        transcript=transcript,
        archive_root=archive_root,
        batch_slug="gate3",
        role="implementer",
        repo_root=git_repo,
    )
    assert result.archive_path.is_file()


def test_archive_refuses_non_ignored_root_inside_repo(git_repo):
    transcript = git_repo.parent / "pane.txt"
    transcript.write_bytes(b"hello\n")
    archive_root = git_repo / "tracked-archive"  # NOT ignored
    with pytest.raises(transcript_archive.ArchiveRootNotIgnored):
        transcript_archive.archive(
            transcript=transcript,
            archive_root=archive_root,
            batch_slug="gate3",
            role="implementer",
            repo_root=git_repo,
        )
    assert not archive_root.exists()
