"""Integration tests for pco-allocate / pco-release CLI subcommands.

These tests exercise the full CLI path against a real (temporary) git
repository. The git worktree add/remove operations are kept minimal and
are always performed against temp directories only — never against the
root checkout, any production worktree, or the PCO-024/PCO-027-032
implementation worktrees.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.cli import main


# ---------------------------------------------------------------------------
# Fixture: minimal real git repo + secondary worktree
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Minimal git repo with one commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "--initial-branch=main"], repo)
    _git(["config", "user.email", "test@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    (repo / "README.md").write_text("test repo\n", encoding="utf-8")
    _git(["add", "README.md"], repo)
    _git(["commit", "-m", "init"], repo)
    return repo


@pytest.fixture()
def secondary_worktree(git_repo: Path, tmp_path: Path) -> Path:
    """Secondary worktree (not the root checkout) with its own .hermes ledger."""
    wt_path = tmp_path / "wt"
    # Create a new branch for the secondary worktree so we don't conflict with main
    _git(["worktree", "add", "-b", "fixture/secondary-wt", str(wt_path)], git_repo)
    ledger_dir = wt_path / ".hermes" / "active-work-ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    return wt_path


# ---------------------------------------------------------------------------
# CLI: pco-allocate subcommand present
# ---------------------------------------------------------------------------


def test_pco_allocate_subcommand_is_registered(capsys):
    """The pco-allocate subcommand must be reachable via --help without error."""
    with pytest.raises(SystemExit) as exc_info:
        main(["pco-allocate", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "lane-id" in out or "allocate" in out.lower()


def test_pco_release_subcommand_is_registered(capsys):
    """The pco-release subcommand must be reachable via --help without error."""
    with pytest.raises(SystemExit) as exc_info:
        main(["pco-release", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "lane-id" in out or "release" in out.lower()


# ---------------------------------------------------------------------------
# CLI: pco-allocate refuses root checkout
# ---------------------------------------------------------------------------


def test_pco_allocate_refuses_root_checkout_via_cli(git_repo: Path, capsys, monkeypatch):
    """pco-allocate must exit non-zero and print a refusal when CWD is the root checkout."""
    monkeypatch.chdir(git_repo)
    ret = main([
        "pco-allocate",
        "--lane-id", "test-lane",
        "--worktree-path", str(git_repo.parent / "test-wt"),
        "--controller-id", "hermes-primary",
        "--branch", "test/branch",
        "--envelope-ref", "none",
        "--no-write-authority",
        "--ledger-root", str(git_repo / ".hermes" / "active-work-ledger"),
        "--repo-root", str(git_repo),
    ])
    assert ret != 0
    out = capsys.readouterr()
    assert "root" in (out.out + out.err).lower() or "refused" in (out.out + out.err).lower()


# ---------------------------------------------------------------------------
# CLI: pco-release refuses root checkout
# ---------------------------------------------------------------------------


def test_pco_release_refuses_root_checkout_via_cli(git_repo: Path, capsys, monkeypatch):
    """pco-release must exit non-zero and print a refusal when CWD is the root checkout."""
    monkeypatch.chdir(git_repo)
    ret = main([
        "pco-release",
        "--lane-id", "test-lane",
        "--controller-id", "hermes-primary",
        "--ledger-root", str(git_repo / ".hermes" / "active-work-ledger"),
        "--repo-root", str(git_repo),
    ])
    assert ret != 0
    out = capsys.readouterr()
    assert "root" in (out.out + out.err).lower() or "refused" in (out.out + out.err).lower()


# ---------------------------------------------------------------------------
# Full allocate + release cycle from secondary worktree
# ---------------------------------------------------------------------------


def test_pco_allocate_refuses_none_envelope_without_opt_in_before_writes(
    secondary_worktree: Path, tmp_path: Path, capsys
):
    """Bare ``--envelope-ref none`` must fail loudly without writing ledger state."""
    new_wt = tmp_path / "allocated-wt"
    ledger = secondary_worktree / ".hermes" / "active-work-ledger"

    ret = main([
        "pco-allocate",
        "--lane-id", "test-lane",
        "--worktree-path", str(new_wt),
        "--controller-id", "hermes-primary",
        "--branch", "implementer/pco-alloc-refuse-test",
        "--envelope-ref", "none",
        "--ledger-root", str(ledger),
        "--repo-root", str(secondary_worktree),
    ])

    out = capsys.readouterr()
    combined = out.out + out.err
    assert ret == 1
    assert "--no-write-authority" in combined
    assert "NO write authority" in combined
    assert not (ledger / "claims" / "hermes-primary" / "test-lane.yaml").exists()
    assert not (ledger / "leases" / "hermes-primary" / "test-lane.yaml").exists()
    assert not new_wt.exists()


def test_allocate_release_cycle(secondary_worktree: Path, tmp_path: Path, capsys):
    """End-to-end: allocate a new worktree on a fresh branch, then release it."""
    new_wt = tmp_path / "allocated-wt"
    ledger = secondary_worktree / ".hermes" / "active-work-ledger"
    # Use a unique branch name that does not exist in the repo yet
    branch = "implementer/pco-alloc-integration-test"

    # Allocate
    ret = main([
        "pco-allocate",
        "--lane-id", "test-lane",
        "--worktree-path", str(new_wt),
        "--controller-id", "hermes-primary",
        "--branch", branch,
        "--envelope-ref", "none",
        "--no-write-authority",
        "--ledger-root", str(ledger),
        "--repo-root", str(secondary_worktree),
    ])
    out = capsys.readouterr()
    assert ret == 0, f"pco-allocate must return 0; ledger: {list(ledger.rglob('*'))}"
    assert "NO write authority" in out.out
    assert "advisory-flagged" in out.out

    claim_path = ledger / "claims" / "hermes-primary" / "test-lane.yaml"
    lease_path = ledger / "leases" / "hermes-primary" / "test-lane.yaml"
    assert claim_path.is_file(), "Claim record must exist after allocate"
    assert lease_path.is_file(), "Lease record must exist after allocate"

    # Release
    ret = main([
        "pco-release",
        "--lane-id", "test-lane",
        "--controller-id", "hermes-primary",
        "--ledger-root", str(ledger),
        "--repo-root", str(secondary_worktree),
    ])
    capsys.readouterr()
    assert ret == 0, "pco-release must return 0"

    updated_claim = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert "released_at" in updated_claim, "Claim must be marked released"
    assert not lease_path.exists(), "Lease must be removed after release"


# ---------------------------------------------------------------------------
# CLI: pco-release exits nonzero on unrecoverable release error (Blocker 2)
# ---------------------------------------------------------------------------


def test_pco_release_exits_nonzero_on_unrecoverable_error(
    secondary_worktree: Path, tmp_path: Path, capsys
):
    """pco-release CLI MUST exit nonzero and print an error when release() raises."""
    from unittest.mock import patch

    ledger = secondary_worktree / ".hermes" / "active-work-ledger"
    # Write a valid claim so the root-checkout check passes and release() is reached
    claim_path = ledger / "claims" / "hermes-primary" / "test-lane.yaml"
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    claim_path.write_text(
        yaml.safe_dump({
            "kind": "active-work-ledger-record",
            "record_type": "claim",
            "schema_version": "1",
            "controller_id": "hermes-primary",
            "lane_id": "test-lane",
            "record_timestamp": "2026-05-23T00:00:00Z",
            "worktree_path": str(tmp_path / "nonexistent-wt"),
            "envelope_ref": "none",
            "lease_seconds": 3600,
            "claimed_at": "2026-05-23T00:00:00Z",
            "last_heartbeat_at": "2026-05-23T00:00:00Z",
        }),
        encoding="utf-8",
    )

    # Make _atomic_write fail so release() hits an unrecoverable error
    with patch(
        "creator_engine_validator.pco_allocator._atomic_write",
        side_effect=OSError("simulated disk full"),
    ):
        ret = main([
            "pco-release",
            "--lane-id", "test-lane",
            "--controller-id", "hermes-primary",
            "--ledger-root", str(ledger),
            "--repo-root", str(secondary_worktree),
        ])

    capsys.readouterr()
    assert ret != 0, (
        "pco-release must exit nonzero when release() encounters an unrecoverable error"
    )
