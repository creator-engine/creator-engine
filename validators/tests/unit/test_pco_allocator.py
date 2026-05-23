"""Unit tests for the PCO Slice 2R worktree allocator runtime (PCO-027 through PCO-032)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from creator_engine_validator.pco_allocator import (
    CONTROLLER_ID_ENV,
    AllocationError,
    PcoAllocatorError,
    PcoConflictError,
    RootCheckoutRefused,
    allocate,
    guard,
    is_root_checkout,
    release,
    resolve_controller_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_worktree_root(base: Path) -> Path:
    """Make a directory that looks like a git worktree (not the main checkout)."""
    wt = base / "worktree"
    wt.mkdir(parents=True, exist_ok=True)
    (wt / ".git").write_text("gitdir: ../../.git/worktrees/test\n", encoding="utf-8")
    return wt


def _make_root_checkout(base: Path) -> Path:
    """Make a directory that looks like the root (main) checkout."""
    root = base / "root"
    root.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    return root


def _make_ledger_root(base: Path) -> Path:
    ledger = base / ".hermes" / "active-work-ledger"
    ledger.mkdir(parents=True, exist_ok=True)
    return ledger


def _write_claim(ledger_root: Path, controller_id: str, lane_id: str, record: dict) -> Path:
    path = ledger_root / "claims" / controller_id / f"{lane_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record), encoding="utf-8")
    return path


def _write_lease(ledger_root: Path, controller_id: str, lane_id: str, record: dict) -> Path:
    path = ledger_root / "leases" / controller_id / f"{lane_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record), encoding="utf-8")
    return path


def _valid_claim(controller_id: str, lane_id: str, worktree_path: str) -> dict:
    return {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller_id,
        "lane_id": lane_id,
        "record_timestamp": "source-controlled:.hermes/active-work-ledger/claims/placeholder.yaml",
        "worktree_path": worktree_path,
        "envelope_ref": ".hermes/envelopes/test-envelope.md",
        "lease_seconds": 3600,
        "claimed_at": "source-controlled:.hermes/active-work-ledger/claims/placeholder.yaml",
        "last_heartbeat_at": "source-controlled:.hermes/active-work-ledger/claims/placeholder.yaml",
    }


def _valid_lease(controller_id: str, lane_id: str, worktree_path: str) -> dict:
    return {
        "kind": "worktree-lease-record",
        "record_type": "worktree_lease",
        "schema_version": "1",
        "controller_id": controller_id,
        "lane_id": lane_id,
        "record_timestamp": "2026-05-23T00:00:00Z",
        "lease_id": f"lease-{lane_id}-001",
        "worktree_path": worktree_path,
        "acquired_at": "2026-05-23T00:00:00Z",
        "lease_seconds": 3600,
        "expires_at": "9999-01-01T00:00:00Z",
    }


def _noop_git(*args: Any, **kwargs: Any) -> None:
    """Test double that does nothing (git worktree add succeeds)."""


def _fail_git(*args: Any, **kwargs: Any) -> None:
    """Test double that simulates git worktree add failure."""
    raise RuntimeError("git worktree add: simulated failure")


def _noop_git_remove(*args: Any, **kwargs: Any) -> None:
    """Test double for git worktree remove."""


# ---------------------------------------------------------------------------
# PCO-031: is_root_checkout
# ---------------------------------------------------------------------------


def test_is_root_checkout_when_dot_git_is_directory(tmp_path: Path):
    root = _make_root_checkout(tmp_path)
    assert is_root_checkout(root) is True


def test_is_not_root_checkout_when_dot_git_is_file(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    assert is_root_checkout(wt) is False


def test_is_not_root_checkout_when_no_dot_git(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert is_root_checkout(plain) is False


# ---------------------------------------------------------------------------
# Controller identity resolution
# ---------------------------------------------------------------------------


def test_resolve_controller_id_from_env(tmp_path: Path):
    with patch.dict(os.environ, {CONTROLLER_ID_ENV: "nefarious-laptop-a"}):
        result = resolve_controller_id(tmp_path)
    assert result == "nefarious-laptop-a"


def test_resolve_controller_id_from_identity_file(tmp_path: Path):
    id_file = tmp_path / ".hermes" / "controller-id"
    id_file.parent.mkdir(parents=True)
    id_file.write_text("hermes-primary\n", encoding="utf-8")
    with patch.dict(os.environ, {}, clear=True):
        result = resolve_controller_id(tmp_path)
    assert result == "hermes-primary"


def test_resolve_controller_id_from_claims_dir(tmp_path: Path):
    claims_dir = tmp_path / ".hermes" / "active-work-ledger" / "claims" / "hermes-primary"
    claims_dir.mkdir(parents=True)
    (claims_dir / "lane-a.yaml").write_text("{}", encoding="utf-8")
    with patch.dict(os.environ, {}, clear=True):
        result = resolve_controller_id(tmp_path)
    assert result == "hermes-primary"


def test_resolve_controller_id_returns_none_when_no_convention(tmp_path: Path):
    with patch.dict(os.environ, {}, clear=True):
        result = resolve_controller_id(tmp_path)
    assert result is None


def test_env_takes_precedence_over_file(tmp_path: Path):
    id_file = tmp_path / ".hermes" / "controller-id"
    id_file.parent.mkdir(parents=True)
    id_file.write_text("file-controller\n", encoding="utf-8")
    with patch.dict(os.environ, {CONTROLLER_ID_ENV: "env-controller"}):
        result = resolve_controller_id(tmp_path)
    assert result == "env-controller"


# ---------------------------------------------------------------------------
# PCO-031: allocate and release refuse root checkout
# ---------------------------------------------------------------------------


def test_allocate_refuses_root_checkout(tmp_path: Path):
    root = _make_root_checkout(tmp_path)
    ledger = _make_ledger_root(root)
    with pytest.raises(RootCheckoutRefused):
        allocate(
            repo_root=root,
            ledger_root=ledger,
            lane_id="test-lane",
            worktree_path=tmp_path / "new-worktree",
            envelope_ref=".hermes/envelopes/test.md",
            branch="test/branch",
            controller_id="hermes-primary",
        )


def test_release_refuses_root_checkout(tmp_path: Path):
    root = _make_root_checkout(tmp_path)
    ledger = _make_ledger_root(root)
    with pytest.raises(RootCheckoutRefused):
        release(
            repo_root=root,
            ledger_root=ledger,
            lane_id="test-lane",
            controller_id="hermes-primary",
        )


# ---------------------------------------------------------------------------
# PCO-030: guard() callable for pane-launch gating
# ---------------------------------------------------------------------------


def test_guard_returns_ok_for_empty_ledger(tmp_path: Path):
    ledger = _make_ledger_root(tmp_path)
    result = guard(ledger)
    assert result.ok


def test_guard_detects_worktree_conflict(tmp_path: Path):
    ledger = _make_ledger_root(tmp_path)
    claim_a = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/shared")
    claim_b = _valid_claim("nefarious-laptop-a", "pco-lane-b", "/worktrees/shared")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim_a)
    _write_claim(ledger, "nefarious-laptop-a", "pco-lane-b", claim_b)

    result = guard(ledger)
    assert not result.ok
    assert any("PCO-010" in e.code for e in result.errors)


def test_guard_passes_non_conflicting_claims(tmp_path: Path):
    ledger = _make_ledger_root(tmp_path)
    claim_a = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/alpha")
    claim_b = _valid_claim("nefarious-laptop-a", "pco-lane-b", "/worktrees/beta")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim_a)
    _write_claim(ledger, "nefarious-laptop-a", "pco-lane-b", claim_b)

    result = guard(ledger)
    assert result.ok, [e.format() for e in result.errors]


def test_guard_is_callable_without_side_effects(tmp_path: Path):
    """PCO-030: guard must not spawn panes or mutate filesystem state."""
    ledger = _make_ledger_root(tmp_path)
    files_before = sorted(str(p) for p in ledger.rglob("*"))
    guard(ledger)
    files_after = sorted(str(p) for p in ledger.rglob("*"))
    assert files_before == files_after


# ---------------------------------------------------------------------------
# PCO-027: allocate() — validation before mutation
# ---------------------------------------------------------------------------


def test_allocate_refuses_when_conflicts_exist(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim_a = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/shared")
    claim_b = _valid_claim("nefarious-laptop-a", "pco-lane-b", "/worktrees/shared")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim_a)
    _write_claim(ledger, "nefarious-laptop-a", "pco-lane-b", claim_b)

    with pytest.raises(PcoConflictError):
        allocate(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-new",
            worktree_path=tmp_path / "new-wt",
            envelope_ref=".hermes/envelopes/test.md",
            branch="test/branch",
            controller_id="hermes-primary",
            _git_fn=_noop_git,
        )


def test_allocate_no_files_written_when_guard_fails(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    # Force conflict
    claim_a = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/shared")
    claim_b = _valid_claim("nefarious-laptop-a", "pco-lane-b", "/worktrees/shared")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim_a)
    _write_claim(ledger, "nefarious-laptop-a", "pco-lane-b", claim_b)
    files_before = set(str(p) for p in ledger.rglob("*") if p.is_file())

    with pytest.raises(PcoConflictError):
        allocate(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-new",
            worktree_path=tmp_path / "new-wt",
            envelope_ref=".hermes/envelopes/test.md",
            branch="test/branch",
            controller_id="hermes-primary",
            _git_fn=_noop_git,
        )

    files_after = set(str(p) for p in ledger.rglob("*") if p.is_file())
    new_files = files_after - files_before
    # No new records should be written (only the lock file is permitted)
    non_lock_new = {f for f in new_files if ".lock" not in f}
    assert not non_lock_new, f"Unexpected files written on conflict: {non_lock_new}"


# ---------------------------------------------------------------------------
# PCO-027: allocate() — proposed-state validation (Blocker 1)
# ---------------------------------------------------------------------------


def test_allocate_refuses_same_controller_lane_active_claim(tmp_path: Path):
    """Allocate MUST refuse if an active (unreleased) claim already exists for same controller/lane."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    existing = _valid_claim("hermes-primary", "pco-lane-a", str(tmp_path / "existing-wt"))
    _write_claim(ledger, "hermes-primary", "pco-lane-a", existing)

    with pytest.raises(PcoConflictError):
        allocate(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-a",
            worktree_path=tmp_path / "new-wt",
            envelope_ref=".hermes/envelopes/test.md",
            branch="implementer/test",
            controller_id="hermes-primary",
            _git_fn=_noop_git,
        )


def test_allocate_refuses_proposed_worktree_conflict_with_single_existing_claim(tmp_path: Path):
    """Allocate MUST refuse when proposed worktree_path conflicts with another controller's single live claim.

    The existing guard only checks the current ledger, so with just one claim
    there is no cross-controller worktree conflict yet.  The proposed-state check
    must detect it before any mutation.
    """
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    shared_path = str(tmp_path / "shared-wt")
    existing = _valid_claim("hermes-primary", "pco-lane-a", shared_path)
    _write_claim(ledger, "hermes-primary", "pco-lane-a", existing)

    with pytest.raises(PcoConflictError):
        allocate(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-b",
            worktree_path=Path(shared_path),
            envelope_ref=".hermes/envelopes/test.md",
            branch="implementer/test",
            controller_id="nefarious-laptop-a",
            _git_fn=_noop_git,
        )


def test_allocate_proposed_state_conflict_no_new_files_and_no_git_call(tmp_path: Path):
    """Failed proposed-state validation MUST leave no new files and MUST NOT call git worktree add."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    shared_path = str(tmp_path / "shared-wt")
    existing = _valid_claim("hermes-primary", "pco-lane-a", shared_path)
    _write_claim(ledger, "hermes-primary", "pco-lane-a", existing)
    files_before = set(str(p) for p in ledger.rglob("*") if p.is_file())

    git_called: list[Any] = []

    def tracking_git(*args: Any, **kwargs: Any) -> None:
        git_called.append(args)

    with pytest.raises(PcoConflictError):
        allocate(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-b",
            worktree_path=Path(shared_path),
            envelope_ref=".hermes/envelopes/test.md",
            branch="implementer/test",
            controller_id="nefarious-laptop-a",
            _git_fn=tracking_git,
        )

    assert not git_called, "git worktree add MUST NOT be called when proposed-state validation fails"
    files_after = set(str(p) for p in ledger.rglob("*") if p.is_file())
    non_lock_new = {f for f in (files_after - files_before) if ".lock" not in f}
    assert not non_lock_new, f"No new ledger files should be written on proposed-state conflict: {non_lock_new}"


def test_allocate_refuses_existing_live_lease_worktree_conflict_before_mutation(tmp_path: Path):
    """Allocate MUST stage proposed lease state and refuse PCO-022 before lease write/git add."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    shared_path = str(tmp_path / "shared-wt")
    existing_lease = _valid_lease("hermes-primary", "pco-lane-a", shared_path)
    _write_lease(ledger, "hermes-primary", "pco-lane-a", existing_lease)
    files_before = set(str(p) for p in ledger.rglob("*") if p.is_file())
    git_called: list[Any] = []

    def tracking_git(*args: Any, **kwargs: Any) -> None:
        git_called.append(args)

    with pytest.raises(PcoConflictError):
        allocate(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-b",
            worktree_path=Path(shared_path),
            envelope_ref=".hermes/envelopes/test.md",
            branch="implementer/test",
            controller_id="nefarious-laptop-a",
            _git_fn=tracking_git,
        )

    assert not git_called, "git worktree add MUST NOT run after proposed lease conflict"
    files_after = set(str(p) for p in ledger.rglob("*") if p.is_file())
    non_lock_new = {f for f in (files_after - files_before) if ".lock" not in f}
    assert not non_lock_new, f"No new ledger files should be written on proposed lease conflict: {non_lock_new}"


def test_allocate_refuses_when_proposed_lease_would_make_existing_claim_uncovered(tmp_path: Path):
    """Allocate MUST refuse if staging the first lease would make an existing live claim fail PCO-021."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    legacy_claim = _valid_claim("hermes-primary", "pco-lane-a", str(tmp_path / "legacy-wt"))
    _write_claim(ledger, "hermes-primary", "pco-lane-a", legacy_claim)
    assert guard(ledger).ok, "zero-lease legacy state is backward-compatible before proposed allocation"
    files_before = set(str(p) for p in ledger.rglob("*") if p.is_file())
    git_called: list[Any] = []

    def tracking_git(*args: Any, **kwargs: Any) -> None:
        git_called.append(args)

    with pytest.raises(PcoConflictError):
        allocate(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-b",
            worktree_path=tmp_path / "allocated-wt",
            envelope_ref=".hermes/envelopes/test.md",
            branch="implementer/test",
            controller_id="nefarious-laptop-a",
            _git_fn=tracking_git,
        )

    assert not git_called, "git worktree add MUST NOT run when proposed state fails PCO-021"
    files_after = set(str(p) for p in ledger.rglob("*") if p.is_file())
    non_lock_new = {f for f in (files_after - files_before) if ".lock" not in f}
    assert not non_lock_new, f"No new ledger files should be written when proposed state fails: {non_lock_new}"


# ---------------------------------------------------------------------------
# PCO-027: allocate() — successful allocation
# ---------------------------------------------------------------------------


def test_allocate_creates_lease_claim_and_event(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)

    allocate(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        worktree_path=tmp_path / "allocated-wt",
        envelope_ref=".hermes/envelopes/test.md",
        branch="implementer/pco-test",
        controller_id="hermes-primary",
        _git_fn=_noop_git,
    )

    lease_files = list((ledger / "claims").rglob("*.yaml"))
    event_files = list((ledger / "events").rglob("*.yaml"))
    lease_record_files = list((ledger / "leases").rglob("*.yaml"))

    assert len(lease_files) == 1, "Exactly one claim record created"
    assert len(event_files) == 1, "Exactly one event record created"
    assert len(lease_record_files) == 1, "Exactly one lease record created"


def test_allocate_claim_has_correct_fields(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)

    allocate(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        worktree_path=tmp_path / "allocated-wt",
        envelope_ref=".hermes/envelopes/test.md",
        branch="implementer/pco-test",
        controller_id="hermes-primary",
        _git_fn=_noop_git,
    )

    claim_path = ledger / "claims" / "hermes-primary" / "pco-lane-a.yaml"
    assert claim_path.is_file()
    claim = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert claim["kind"] == "active-work-ledger-record"
    assert claim["record_type"] == "claim"
    assert claim["controller_id"] == "hermes-primary"
    assert claim["lane_id"] == "pco-lane-a"
    assert claim["envelope_ref"] == ".hermes/envelopes/test.md"
    assert "worktree_path" in claim
    assert "claimed_at" in claim
    assert "last_heartbeat_at" in claim


def test_allocate_event_is_claim_created(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)

    allocate(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        worktree_path=tmp_path / "allocated-wt",
        envelope_ref="none",
        branch="implementer/pco-test",
        controller_id="hermes-primary",
        _git_fn=_noop_git,
    )

    event_files = list((ledger / "events").rglob("*.yaml"))
    assert event_files
    event = yaml.safe_load(event_files[0].read_text(encoding="utf-8"))
    assert event["event_kind"] == "claim_created"
    assert event["controller_id"] == "hermes-primary"
    assert event["lane_id"] == "pco-lane-a"


def test_allocate_literal_none_envelope_ref_produces_valid_guard_state(tmp_path: Path):
    """The documented literal `none` envelope_ref MUST validate in generated lease/claim state."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)

    allocate(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        worktree_path=tmp_path / "allocated-wt",
        envelope_ref="none",
        branch="implementer/pco-test",
        controller_id="hermes-primary",
        _git_fn=_noop_git,
    )

    result = guard(ledger)
    assert result.ok, [e.format() for e in result.errors]


def test_allocate_lease_written_before_claim_pco029(tmp_path: Path):
    """PCO-029: lease MUST be written before claim."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    write_order: list[str] = []

    original_atomic_write = None

    def tracking_git_fn(*args: Any, **kwargs: Any) -> None:
        # Check that lease exists at the time git runs (between lease and claim)
        if (ledger / "leases").exists():
            lease_files = list((ledger / "leases").rglob("*.yaml"))
            if lease_files:
                write_order.append("lease_before_git")

    allocate(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        worktree_path=tmp_path / "allocated-wt",
        envelope_ref="none",
        branch="implementer/pco-test",
        controller_id="hermes-primary",
        _git_fn=tracking_git_fn,
    )

    assert "lease_before_git" in write_order, "Lease must be written before git worktree add"


# ---------------------------------------------------------------------------
# PCO-027: allocate() — rollback on failure
# ---------------------------------------------------------------------------


def test_allocate_rollback_removes_lease_on_git_failure(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)

    with pytest.raises((AllocationError, RuntimeError)):
        allocate(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-a",
            worktree_path=tmp_path / "allocated-wt",
            envelope_ref=".hermes/envelopes/test.md",
            branch="implementer/pco-test",
            controller_id="hermes-primary",
            _git_fn=_fail_git,
        )

    lease_files = list((ledger / "leases").rglob("*.yaml"))
    assert not lease_files, "Lease must be removed on git failure rollback"


def test_allocate_rollback_leaves_no_claim_on_git_failure(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)

    with pytest.raises((AllocationError, RuntimeError)):
        allocate(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-a",
            worktree_path=tmp_path / "allocated-wt",
            envelope_ref=".hermes/envelopes/test.md",
            branch="implementer/pco-test",
            controller_id="hermes-primary",
            _git_fn=_fail_git,
        )

    claim_files = list((ledger / "claims").rglob("*.yaml"))
    assert not claim_files, "No claim records after git failure rollback"


# ---------------------------------------------------------------------------
# PCO-028: release() — mark claim released
# ---------------------------------------------------------------------------


def test_release_marks_claim_released(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/test")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)

    release(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        controller_id="hermes-primary",
        release_reason="completed",
        _git_fn=_noop_git_remove,
    )

    claim_path = ledger / "claims" / "hermes-primary" / "pco-lane-a.yaml"
    updated = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
    assert "released_at" in updated
    assert updated["release_reason"] == "completed"


def test_release_removes_lease(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/test")
    lease = _valid_lease("hermes-primary", "pco-lane-a", "/worktrees/test")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)
    _write_lease(ledger, "hermes-primary", "pco-lane-a", lease)

    release(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        controller_id="hermes-primary",
        _git_fn=_noop_git_remove,
    )

    lease_path = ledger / "leases" / "hermes-primary" / "pco-lane-a.yaml"
    assert not lease_path.exists(), "Lease file must be removed on release"


def test_release_appends_claim_released_event(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/test")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)

    release(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        controller_id="hermes-primary",
        _git_fn=_noop_git_remove,
    )

    event_files = list((ledger / "events").rglob("*.yaml"))
    assert event_files, "An event record must be emitted on release"
    events = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in event_files]
    release_events = [e for e in events if e.get("event_kind") == "claim_released"]
    assert release_events, "A claim_released event must be emitted"


def test_release_calls_git_worktree_remove(tmp_path: Path):
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    # Create the directory so the existence check allows the git call
    actual_wt = tmp_path / "my-worktree"
    actual_wt.mkdir()
    worktree_path = str(actual_wt)
    claim = _valid_claim("hermes-primary", "pco-lane-a", worktree_path)
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)
    calls: list[Any] = []

    def recording_git_remove(repo_root: Path, wt_path: Path) -> None:
        calls.append(str(wt_path))

    release(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        controller_id="hermes-primary",
        _git_fn=recording_git_remove,
    )

    assert calls, "git worktree remove must be called"
    assert worktree_path in calls[0], "git remove called with correct worktree path"


def test_release_does_not_delete_branch(tmp_path: Path):
    """PCO-028: release MUST NOT delete branches."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/test")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)
    branch_delete_calls: list[Any] = []

    def detect_branch_deletion(*args: Any, **kwargs: Any) -> None:
        if "branch" in str(args) and "delete" in str(args):
            branch_delete_calls.append(args)

    with patch("subprocess.run", side_effect=detect_branch_deletion):
        try:
            release(
                repo_root=wt,
                ledger_root=ledger,
                lane_id="pco-lane-a",
                controller_id="hermes-primary",
                _git_fn=_noop_git_remove,
            )
        except Exception:
            pass

    assert not branch_delete_calls, "release MUST NOT delete branches"


def test_release_is_recoverable_when_claim_already_released(tmp_path: Path):
    """PCO-028: release must not error if claim is already released."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/test")
    claim["released_at"] = "2026-05-23T00:00:00Z"
    claim["release_reason"] = "completed"
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)

    # Should not raise even though claim is already released
    release(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        controller_id="hermes-primary",
        _git_fn=_noop_git_remove,
    )


def test_release_is_recoverable_when_lease_already_removed(tmp_path: Path):
    """PCO-028: release must not error if lease was already removed."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/test")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)
    # No lease file written - simulate mid-sequence recovery

    release(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        controller_id="hermes-primary",
        _git_fn=_noop_git_remove,
    )
    # Must complete without error


def test_release_is_recoverable_when_claim_file_absent(tmp_path: Path):
    """PCO-028: release must tolerate missing claim file (already cleaned up)."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    # No claim file - simulate recovery after partial cleanup

    release(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        controller_id="hermes-primary",
        _git_fn=_noop_git_remove,
    )
    # Must complete without error


# ---------------------------------------------------------------------------
# PCO-028: release() — fail-closed behavior (Blocker 2)
# ---------------------------------------------------------------------------


def test_release_claim_write_failure_raises(tmp_path: Path):
    """Release MUST raise (not silently continue) when claim release-marker write fails."""
    from unittest.mock import patch

    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/test")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)

    with patch(
        "creator_engine_validator.pco_allocator._atomic_write",
        side_effect=OSError("disk full"),
    ):
        with pytest.raises((Exception,)):
            release(
                repo_root=wt,
                ledger_root=ledger,
                lane_id="pco-lane-a",
                controller_id="hermes-primary",
                _git_fn=_noop_git_remove,
            )


def test_release_existing_malformed_claim_raises_without_mutating_lease_or_events(tmp_path: Path):
    """Existing unreadable/malformed claims are unrecoverable; only absent claims are recoverable."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim_path = ledger / "claims" / "hermes-primary" / "pco-lane-a.yaml"
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    claim_path.write_text("kind: [unterminated\n", encoding="utf-8")
    lease = _valid_lease("hermes-primary", "pco-lane-a", "/worktrees/test")
    lease_path = _write_lease(ledger, "hermes-primary", "pco-lane-a", lease)

    with pytest.raises(PcoAllocatorError):
        release(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-a",
            controller_id="hermes-primary",
            _git_fn=_noop_git_remove,
        )

    assert lease_path.exists(), "lease MUST remain when release cannot read an existing claim"
    assert not list((ledger / "events").rglob("*.yaml")), "event MUST NOT be written after claim load failure"


def test_release_existing_schema_invalid_claim_mapping_raises_without_mutation(tmp_path: Path):
    """Existing schema-invalid claim mappings are malformed and MUST fail closed."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim_path = ledger / "claims" / "hermes-primary" / "pco-lane-a.yaml"
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    claim_path.write_text(yaml.safe_dump({"not": "a valid claim record"}), encoding="utf-8")
    lease = _valid_lease("hermes-primary", "pco-lane-a", "/worktrees/test")
    lease_path = _write_lease(ledger, "hermes-primary", "pco-lane-a", lease)

    with pytest.raises(PcoAllocatorError):
        release(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-a",
            controller_id="hermes-primary",
            _git_fn=_noop_git_remove,
        )

    assert lease_path.exists(), "lease MUST remain when existing claim schema is invalid"
    assert not list((ledger / "events").rglob("*.yaml")), "event MUST NOT be written after invalid claim schema"


def test_release_lease_removal_failure_raises(tmp_path: Path):
    """Release MUST raise (not silently continue) when lease file removal fails."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/test")
    lease = _valid_lease("hermes-primary", "pco-lane-a", "/worktrees/test")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)
    _write_lease(ledger, "hermes-primary", "pco-lane-a", lease)

    # Make the lease directory non-writable so unlink() raises PermissionError
    lease_dir = ledger / "leases" / "hermes-primary"
    lease_dir.chmod(0o555)
    try:
        with pytest.raises((Exception,)):
            release(
                repo_root=wt,
                ledger_root=ledger,
                lane_id="pco-lane-a",
                controller_id="hermes-primary",
                _git_fn=_noop_git_remove,
            )
    finally:
        lease_dir.chmod(0o755)


def test_release_event_write_failure_raises(tmp_path: Path):
    """Release MUST raise (not silently continue) when claim_released event write fails."""
    import creator_engine_validator.pco_allocator as _pco_mod
    from unittest.mock import patch

    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    claim = _valid_claim("hermes-primary", "pco-lane-a", "/worktrees/test")
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)

    _real_atomic_write = _pco_mod._atomic_write

    def fail_for_events(path: Path, content: str) -> None:
        if "events" in str(path):
            raise OSError("disk full on events")
        _real_atomic_write(path, content)

    with patch(
        "creator_engine_validator.pco_allocator._atomic_write",
        side_effect=fail_for_events,
    ):
        with pytest.raises((Exception,)):
            release(
                repo_root=wt,
                ledger_root=ledger,
                lane_id="pco-lane-a",
                controller_id="hermes-primary",
                _git_fn=_noop_git_remove,
            )


def test_release_git_worktree_remove_failure_raises_when_path_exists(tmp_path: Path):
    """Release MUST raise (not silently continue) when git worktree remove fails for an existing worktree."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    actual_wt = tmp_path / "live-worktree"
    actual_wt.mkdir()
    claim = _valid_claim("hermes-primary", "pco-lane-a", str(actual_wt))
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)

    def always_fail_git(repo_root: Path, wt_path: Path) -> None:
        raise RuntimeError("git worktree remove: simulated failure")

    with pytest.raises((Exception,)):
        release(
            repo_root=wt,
            ledger_root=ledger,
            lane_id="pco-lane-a",
            controller_id="hermes-primary",
            _git_fn=always_fail_git,
        )


def test_release_is_recoverable_when_worktree_already_removed(tmp_path: Path):
    """Release MUST NOT call git worktree remove when the worktree directory does not exist."""
    wt = _make_worktree_root(tmp_path)
    ledger = _make_ledger_root(wt)
    nonexistent_wt = str(tmp_path / "nonexistent-wt")
    claim = _valid_claim("hermes-primary", "pco-lane-a", nonexistent_wt)
    _write_claim(ledger, "hermes-primary", "pco-lane-a", claim)

    git_called: list[Any] = []

    def record_call(repo_root: Path, wt_path: Path) -> None:
        git_called.append(str(wt_path))

    release(
        repo_root=wt,
        ledger_root=ledger,
        lane_id="pco-lane-a",
        controller_id="hermes-primary",
        _git_fn=record_call,
    )

    assert not git_called, (
        "git worktree remove MUST NOT be called when worktree path does not exist on disk"
    )
