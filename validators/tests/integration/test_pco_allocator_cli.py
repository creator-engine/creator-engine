"""Integration tests for pco-allocate / pco-release CLI subcommands.

These tests exercise the full CLI path against a real (temporary) git
repository. The git worktree add/remove operations are kept minimal and
are always performed against temp directories only — never against the
root checkout, any production worktree, or the PCO-024/PCO-027-032
implementation worktrees.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.checks.pane_registry import validate_pane_registry_record
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


def test_pco_release_lapsed_terminalizes_matching_pane_registry_record(
    secondary_worktree: Path, tmp_path: Path, capsys
):
    """A stale/lapsed lane release also closes the matching Pane Registry record."""
    new_wt = tmp_path / "allocated-wt"
    ledger = secondary_worktree / ".hermes" / "active-work-ledger"
    branch = "implementer/pco-lapsed-pane-test"

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
    capsys.readouterr()
    assert ret == 0

    claim_path = ledger / "claims" / "hermes-primary" / "test-lane.yaml"
    pane_path = ledger / "panes" / "hermes-primary" / "test-lane.yaml"
    pane_path.parent.mkdir(parents=True, exist_ok=True)
    pane_record = {
        "kind": "pane-registry-record",
        "record_type": "pane_identity",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "test-lane",
        "claim_ref": "claims/hermes-primary/test-lane.yaml",
        "host_id": "host-one",
        "pane_id": "pane-test1",
        "role": "implementer",
        "status": "active",
        "record_timestamp": "2026-05-23T00:00:00Z",
        "registered_at": "2026-05-23T00:00:00Z",
        "last_seen_at": "2026-05-23T00:00:00Z",
        "visibility": "operator_visible",
        "terminal": {
            "kind": "tmux",
            "session_id": "ce-lane",
            "window_id": "0",
            "pane_id": "%1",
        },
        "claim_record_sha256": hashlib.sha256(
            claim_path.read_bytes()
        ).hexdigest(),
        "worktree_path": str(new_wt),
        "branch": branch,
    }
    assert validate_pane_registry_record(pane_record, pane_path) == []
    pane_path.write_text(
        yaml.safe_dump(pane_record, sort_keys=True), encoding="utf-8"
    )

    ret = main([
        "pco-release",
        "--lane-id", "test-lane",
        "--controller-id", "hermes-primary",
        "--ledger-root", str(ledger),
        "--repo-root", str(secondary_worktree),
        "--release-reason", "lapsed",
    ])
    capsys.readouterr()
    assert ret == 0

    updated_pane = yaml.safe_load(pane_path.read_text(encoding="utf-8"))
    assert updated_pane["status"] == "closed"
    assert updated_pane["close_reason"] == "lapsed"
    assert "closed_at" in updated_pane
    assert updated_pane["claim_record_sha256"] == hashlib.sha256(
        claim_path.read_bytes()
    ).hexdigest()
    assert validate_pane_registry_record(updated_pane, pane_path) == []


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


# ---------------------------------------------------------------------------
# ce-ops#43 §10.8 pco-release-leg-is-reused — the seat/venue reaper's tmux
# executor releases the worktree through the EXISTING creator-engine-validator
# pco-release CLI (subprocess+DATA), then verifies the claim/lease/event/worktree
# facts WITHOUT deleting the branch. Exercises the REAL pco-release CLI in-process.
# ---------------------------------------------------------------------------

import contextlib as _contextlib
import io as _io
from types import SimpleNamespace as _NS

from creator_engine_validator import reaper_executors as _reaper_executors
from creator_engine_validator import seat_reaper as _seat_reaper


def _bare_plan(**over):
    base = dict(
        seat_id="run-x", run_id="run-x", classification=_seat_reaper.CLASS_ELIGIBLE,
        release_reason=_seat_reaper.RELEASE_REASON_COMPLETED, state_root=Path("."),
        dispatch={}, dispatch_path=Path("."), events_path=Path("."), archive_root=Path("."),
        batch_slug="run-x", role="implementer", terminal=None, harness_session_id=None,
        transcript_ref=None, archive_expected=False, lane_id=None, controller_id=None,
        ledger_root=None, worktree_path=None, pane_registry_path=None,
    )
    base.update(over)
    return _seat_reaper.RetirementPlan(**base)


def test_8_pco_release_leg_is_reused(secondary_worktree: Path, tmp_path: Path):
    new_wt = tmp_path / "reaper-allocated-wt"
    ledger = secondary_worktree / ".hermes" / "active-work-ledger"
    branch = "implementer/ce43-reaper-release-test"

    # allocate a real worktree + claim + lease on a fresh branch (the fixture under test)
    assert main([
        "pco-allocate", "--lane-id", "reap-lane", "--worktree-path", str(new_wt),
        "--controller-id", "ctrl-x", "--branch", branch, "--envelope-ref", "none",
        "--no-write-authority", "--ledger-root", str(ledger),
        "--repo-root", str(secondary_worktree),
    ]) == 0
    claim_path = ledger / "claims" / "ctrl-x" / "reap-lane.yaml"
    lease_path = ledger / "leases" / "ctrl-x" / "reap-lane.yaml"
    assert claim_path.is_file() and lease_path.is_file() and new_wt.is_dir()

    # an in-process runner that drives the REAL creator-engine-validator CLI for the
    # `pco-release` argv the executor composes — subprocess+DATA, no PATH dependency.
    recorded: list[list[str]] = []

    def runner(argv, **kw):
        argv = list(argv)
        recorded.append(argv)
        buf_out, buf_err = _io.StringIO(), _io.StringIO()
        with _contextlib.redirect_stdout(buf_out), _contextlib.redirect_stderr(buf_err):
            rc = main(argv[1:])  # argv[0] is the exe name
        return _NS(returncode=rc, stdout=buf_out.getvalue(), stderr=buf_err.getvalue())

    executor = _reaper_executors.TmuxExecutor(runner=runner)
    plan = _bare_plan(
        lane_id="reap-lane", controller_id="ctrl-x", ledger_root=ledger, worktree_path=new_wt,
        release_reason=_seat_reaper.RELEASE_REASON_COMPLETED,
    )
    result = executor.release_worktree(plan)

    # the executor invoked the EXISTING pco-release leg
    assert recorded and recorded[0][1] == "pco-release"
    assert result.status == _seat_reaper.STEP_SUCCEEDED, result.detail

    # the verified facts (§6.4): claim released, lease gone, claim_released event, worktree gone
    released = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert released.get("released_at") and released.get("release_reason") == "completed"
    assert not lease_path.exists()
    events = list((ledger / "events").rglob("*.yaml"))
    assert any(
        yaml.safe_load(p.read_text()).get("event_kind") == "claim_released" for p in events
    )
    assert not new_wt.exists()

    # NO branch deletion — the fresh branch still exists in the repo
    branches = _git(["branch", "--list", branch], secondary_worktree).stdout
    assert branch in branches


def test_8b_pco_release_root_checkout_refusal_is_surfaced(git_repo: Path):
    """When pco-release refuses the root checkout, the executor surfaces it as a
    FAILED step flagged root_checkout_refused (the policy escalates, never bypasses)."""
    def runner(argv, **kw):
        argv = list(argv)
        buf_out, buf_err = _io.StringIO(), _io.StringIO()
        with _contextlib.redirect_stdout(buf_out), _contextlib.redirect_stderr(buf_err):
            rc = main(argv[1:])
        return _NS(returncode=rc, stdout=buf_out.getvalue(), stderr=buf_err.getvalue())

    ledger = git_repo / ".hermes" / "active-work-ledger"
    ledger.mkdir(parents=True, exist_ok=True)
    executor = _reaper_executors.TmuxExecutor(runner=runner)
    # repo_root == the ROOT checkout (git_repo) → pco-release refuses
    plan = _bare_plan(
        lane_id="reap-lane", controller_id="ctrl-x", ledger_root=ledger, worktree_path=git_repo,
    )
    result = executor.release_worktree(plan)
    assert result.status == _seat_reaper.STEP_FAILED
    assert result.data.get("root_checkout_refused") is True
