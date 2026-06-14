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


# ---------------------------------------------------------------------------
# ce-ops#43 — the reaper tmux executor archives a seat's transcript through the
# EXISTING `ce lane archive --json` leg (subprocess+DATA, §6.2): it resolves the
# transcript by exact harness_session_id, composes the argv, and consumes only
# the JSON archive_path + sha256. Unit-level with a fake runner.
# ---------------------------------------------------------------------------

import json as _json
from types import SimpleNamespace as _NS

from creator_engine_validator import reaper_executors as _reaper_executors
from creator_engine_validator import seat_reaper as _seat_reaper


def _archive_plan(tmp_path, *, harness_session_id=None, transcript_ref=None,
                  archive_expected=True, worktree_path=None):
    return _seat_reaper.RetirementPlan(
        seat_id="run-x", run_id="run-x", classification=_seat_reaper.CLASS_ELIGIBLE,
        release_reason="completed", state_root=tmp_path, dispatch={}, dispatch_path=tmp_path,
        events_path=tmp_path, archive_root=tmp_path / "arch", batch_slug="demo-scope",
        role="implementer", terminal=None, harness_session_id=harness_session_id,
        transcript_ref=transcript_ref, archive_expected=archive_expected, lane_id=None,
        controller_id=None, ledger_root=None, worktree_path=worktree_path, pane_registry_path=None,
    )


def test_reaper_archive_resolves_session_id_and_consumes_json(tmp_path):
    # a transcript stamped at a KNOWN session-id key under the harness projects dir
    sid = "00000000-0000-4000-8000-000000000000"
    projects = tmp_path / "claude" / "projects" / "some-project"
    projects.mkdir(parents=True)
    transcript = projects / f"{sid}.jsonl"
    transcript.write_text('{"type":"x"}\n', encoding="utf-8")

    captured = {}

    def runner(argv, **kw):
        argv = list(argv)
        captured["argv"] = argv
        # the fake `ce lane archive --json` emits the path+sha contract
        return _NS(returncode=0, stdout=_json.dumps(
            {"archive_path": str(tmp_path / "arch" / "a.txt"), "sha256": "f" * 64}), stderr="")

    executor = _reaper_executors.TmuxExecutor(
        runner=runner, ce_exe="ce", transcript_search_root=tmp_path / "claude" / "projects")
    result = executor.archive_transcript(_archive_plan(tmp_path, harness_session_id=sid))
    assert result.status == _seat_reaper.STEP_SUCCEEDED
    assert result.data["archive_path"].endswith("a.txt") and result.data["sha256"] == "f" * 64
    argv = captured["argv"]
    assert argv[:3] == ["ce", "lane", "archive"]
    assert "--json" in argv
    assert "--transcript" in argv and argv[argv.index("--transcript") + 1] == str(transcript)
    assert "--batch-slug" in argv and argv[argv.index("--batch-slug") + 1] == "demo-scope"
    assert "--role" in argv and argv[argv.index("--role") + 1] == "implementer"


def test_reaper_archive_uses_codex_transcript_ref(tmp_path):
    ref = tmp_path / "codex" / "session.jsonl"
    ref.parent.mkdir(parents=True)
    ref.write_text("{}\n", encoding="utf-8")
    transcript, reason = _reaper_executors.resolve_transcript(
        _archive_plan(tmp_path, transcript_ref=str(ref)), search_root=None)
    assert transcript == ref and reason is None


def test_reaper_archive_missing_when_expected_is_failure(tmp_path):
    executor = _reaper_executors.TmuxExecutor(
        runner=lambda *a, **k: _NS(returncode=0, stdout="{}", stderr=""),
        transcript_search_root=tmp_path / "empty")
    result = executor.archive_transcript(
        _archive_plan(tmp_path, harness_session_id="nope", archive_expected=True))
    assert result.status == _seat_reaper.STEP_FAILED


def test_reaper_archive_not_applicable_when_not_expected_and_absent(tmp_path):
    executor = _reaper_executors.TmuxExecutor(
        runner=lambda *a, **k: _NS(returncode=0, stdout="{}", stderr=""),
        transcript_search_root=tmp_path / "empty")
    result = executor.archive_transcript(
        _archive_plan(tmp_path, harness_session_id="nope", archive_expected=False))
    assert result.status == _seat_reaper.STEP_NOT_APPLICABLE


def test_reaper_archive_ambiguous_session_id_refused(tmp_path):
    sid = "dupe-session"
    for sub in ("p1", "p2"):
        d = tmp_path / "claude" / "projects" / sub
        d.mkdir(parents=True)
        (d / f"{sid}.jsonl").write_text("{}\n", encoding="utf-8")
    transcript, reason = _reaper_executors.resolve_transcript(
        _archive_plan(tmp_path, harness_session_id=sid),
        search_root=tmp_path / "claude" / "projects")
    assert transcript is None and "ambiguous" in reason
