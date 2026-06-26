"""Integration tests for the ``ce`` CLI lane family against temp git repos.

Exercises the full ``verify`` and ``archive`` surfaces end-to-end, including
the git-ignore refusal for archive roots inside a repository. No production
worktree, ledger, or tmux session is touched; every artifact is under
pytest ``tmp_path``.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import ce_cli
pytestmark = pytest.mark.slow



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


def _write_pane_record(ledger: Path, controller="hermes-primary", lane="gate3-lane") -> Path:
    record = {
        "kind": "pane-registry-record",
        "record_type": "pane_identity",
        "schema_version": "1",
        "controller_id": controller,
        "lane_id": lane,
        "claim_ref": f"claims/{controller}/{lane}.yaml",
        "host_id": "operator-host",
        "pane_id": "pane-gate3-lane",
        "role": "implementer",
        "status": "active",
        "record_timestamp": "2026-05-25T05:00:00Z",
        "registered_at": "2026-05-25T05:00:00Z",
        "last_seen_at": "2026-05-25T05:00:00Z",
        "visibility": "operator_visible",
        "terminal": {"kind": "tmux", "session_id": "ce", "window_id": "w", "pane_id": "1"},
    }
    path = ledger / "panes" / controller / f"{lane}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def test_verify_passes_with_completion_report(tmp_path):
    ledger = tmp_path / ".hermes" / "active-work-ledger"
    ledger.mkdir(parents=True)
    _write_pane_record(ledger)
    stop = "CE_PCO_V1_G3_GOVERNED_LANE_LAUNCH_READY_FOR_SOURCE_RATIFICATION"
    transcript = tmp_path / "t.txt"
    transcript.write_text(f"...\n{stop}\n", encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_text(f"status: ready\n{stop}\n", encoding="utf-8")
    ret = ce_cli.main([
        "lane", "verify",
        "--controller-id", "hermes-primary",
        "--lane-id", "gate3-lane",
        "--ledger-root", str(ledger),
        "--transcript", str(transcript),
        "--stop-line", stop,
        "--completion-report", str(report),
    ])
    assert ret == 0


def test_verify_refuses_completion_report_without_stop_line(tmp_path):
    ledger = tmp_path / ".hermes" / "active-work-ledger"
    ledger.mkdir(parents=True)
    _write_pane_record(ledger)
    stop = "CE_PCO_V1_G3_GOVERNED_LANE_LAUNCH_READY_FOR_SOURCE_RATIFICATION"
    transcript = tmp_path / "t.txt"
    transcript.write_text(f"{stop}\n", encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_text("status: ready but no stop line\n", encoding="utf-8")
    ret = ce_cli.main([
        "lane", "verify",
        "--controller-id", "hermes-primary",
        "--lane-id", "gate3-lane",
        "--ledger-root", str(ledger),
        "--transcript", str(transcript),
        "--stop-line", stop,
        "--completion-report", str(report),
    ])
    assert ret != 0


def test_archive_to_ignored_root_inside_repo(git_repo, capsys):
    transcript = git_repo.parent / "pane.txt"
    body = b"transcript content\n"
    transcript.write_bytes(body)
    archive_root = git_repo / ".hermes" / "transcripts"
    ret = ce_cli.main([
        "lane", "archive",
        "--transcript", str(transcript),
        "--archive-root", str(archive_root),
        "--batch-slug", "gate3",
        "--role", "implementer",
        "--repo-root", str(git_repo),
    ])
    assert ret == 0
    out = capsys.readouterr().out
    assert hashlib.sha256(body).hexdigest() in out


def test_archive_refuses_non_ignored_root_inside_repo(git_repo):
    transcript = git_repo.parent / "pane.txt"
    transcript.write_bytes(b"x\n")
    archive_root = git_repo / "tracked-archive"
    ret = ce_cli.main([
        "lane", "archive",
        "--transcript", str(transcript),
        "--archive-root", str(archive_root),
        "--batch-slug", "gate3",
        "--role", "implementer",
        "--repo-root", str(git_repo),
    ])
    assert ret != 0
    assert not archive_root.exists()
