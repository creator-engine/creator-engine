from __future__ import annotations

from pathlib import Path

import yaml

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.active_work_ledger_conflicts import (
    CHECK_NAME,
    CODE_CLAIM_REQUIRES_LEASE,
    CODE_EVENT_ID_CONFLICT,
    CODE_EVENT_REF,
    CODE_HEARTBEAT_MONOTONIC,
    CODE_HEARTBEAT_REF,
    CODE_LANE_CONFLICT,
    CODE_LEASE_INVALID_RECORD,
    CODE_WORKTREE_CONFLICT,
    CODE_WORKTREE_LEASE_CONFLICT,
    run,
)


def valid_claim_record() -> dict:
    return {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice0-author",
        "record_timestamp": "source-controlled:.hermes/active-work-ledger/claims/hermes-primary/pco-slice0-author.yaml",
        "worktree_path": "/home/example/projects/creator-engine-worktrees/pco-slice0",
        "envelope_ref": ".hermes/envelopes/pco-slice0.md",
        "lease_seconds": 3600,
        "claimed_at": "source-controlled:.hermes/active-work-ledger/claims/hermes-primary/pco-slice0-author.yaml",
        "last_heartbeat_at": "source-controlled:.hermes/active-work-ledger/claims/hermes-primary/pco-slice0-author.yaml",
    }


def valid_heartbeat_record() -> dict:
    return {
        "kind": "active-work-ledger-record",
        "record_type": "heartbeat",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice0-author",
        "record_timestamp": "2026-05-20T03:31:00Z",
        "claim_ref": "claims/hermes-primary/pco-slice0-author.yaml",
        "heartbeat_sequence": 1,
        "emitted_at": "2026-05-20T03:31:00Z",
    }


def valid_event_record() -> dict:
    return {
        "kind": "active-work-ledger-record",
        "record_type": "event",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice0-author",
        "record_timestamp": "2026-05-20T03:30:31Z",
        "event_kind": "claim_created",
        "event_id": "claim-created-001",
        "event_timestamp": "2026-05-20T03:30:31Z",
    }


def _write_record(path: Path, record: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record), encoding="utf-8")
    return path


def _claim_path(root: Path, controller_id: str, lane_id: str) -> Path:
    return root / "claims" / controller_id / f"{lane_id}.yaml"


def test_conflict_check_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_WORKTREE_CONFLICT in checks[CHECK_NAME].frs


def test_non_conflicting_live_claims_pass(tmp_path: Path):
    claim_a = valid_claim_record()
    claim_a["controller_id"] = "hermes-primary"
    claim_a["lane_id"] = "pco-slice-a"
    claim_a["worktree_path"] = "/worktrees/pco-slice-a"

    claim_b = valid_claim_record()
    claim_b["controller_id"] = "nefarious-laptop-a"
    claim_b["lane_id"] = "pco-slice-b"
    claim_b["worktree_path"] = "/worktrees/pco-slice-b"

    _write_record(_claim_path(tmp_path, "hermes-primary", "pco-slice-a"), claim_a)
    _write_record(_claim_path(tmp_path, "nefarious-laptop-a", "pco-slice-b"), claim_b)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_duplicate_live_lane_for_same_controller_fails(tmp_path: Path):
    claim_a = valid_claim_record()
    claim_a["controller_id"] = "hermes-primary"
    claim_a["lane_id"] = "pco-slice-a"
    claim_a["worktree_path"] = "/worktrees/pco-slice-a"

    claim_b = valid_claim_record()
    claim_b["controller_id"] = "hermes-primary"
    claim_b["lane_id"] = "pco-slice-a"
    claim_b["worktree_path"] = "/worktrees/pco-slice-a-2"

    _write_record(tmp_path / "claims" / "hermes-primary" / "pco-slice-a.yaml", claim_a)
    _write_record(tmp_path / "claims" / "hermes-primary" / "pco-slice-a-copy.yaml", claim_b)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_LANE_CONFLICT for error in result.errors)


def test_heartbeat_sequence_must_be_monotonic_for_claim(tmp_path: Path):
    claim = valid_claim_record()
    claim_path = _claim_path(tmp_path, "hermes-primary", "pco-slice0-author")
    _write_record(claim_path, claim)

    heartbeat_a = valid_heartbeat_record()
    heartbeat_a["claim_ref"] = claim_path.relative_to(tmp_path).as_posix()
    heartbeat_a["heartbeat_sequence"] = 2
    heartbeat_a["emitted_at"] = "2026-05-20T03:32:00Z"

    heartbeat_b = valid_heartbeat_record()
    heartbeat_b["claim_ref"] = claim_path.relative_to(tmp_path).as_posix()
    heartbeat_b["heartbeat_sequence"] = 1
    heartbeat_b["emitted_at"] = "2026-05-20T03:33:00Z"

    _write_record(tmp_path / "heartbeats" / "hermes-primary" / "pco-slice0-author-002.yaml", heartbeat_a)
    _write_record(tmp_path / "heartbeats" / "hermes-primary" / "pco-slice0-author-001-late.yaml", heartbeat_b)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_HEARTBEAT_MONOTONIC for error in result.errors)


def test_event_ids_must_be_unique_within_controller_lane_day(tmp_path: Path):
    event_a = valid_event_record()
    event_a["event_id"] = "claim-created-001"
    event_a["event_timestamp"] = "2026-05-20T03:30:31Z"

    event_b = valid_event_record()
    event_b["event_id"] = "claim-created-001"
    event_b["event_timestamp"] = "2026-05-20T04:30:31Z"

    _write_record(tmp_path / "events" / "2026" / "05" / "20" / "event-a.yaml", event_a)
    _write_record(tmp_path / "events" / "2026" / "05" / "20" / "event-b.yaml", event_b)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_EVENT_ID_CONFLICT for error in result.errors)


def test_live_worktree_claim_collision_across_controllers_fails(tmp_path: Path):
    claim_a = valid_claim_record()
    claim_a["controller_id"] = "hermes-primary"
    claim_a["lane_id"] = "pco-slice-a"
    claim_a["worktree_path"] = "/worktrees/shared"

    claim_b = valid_claim_record()
    claim_b["controller_id"] = "nefarious-laptop-a"
    claim_b["lane_id"] = "pco-slice-b"
    claim_b["worktree_path"] = "/worktrees/shared/"

    _write_record(_claim_path(tmp_path, "hermes-primary", "pco-slice-a"), claim_a)
    _write_record(_claim_path(tmp_path, "nefarious-laptop-a", "pco-slice-b"), claim_b)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_WORKTREE_CONFLICT for error in result.errors)
    assert any("/worktrees/shared" in error.message for error in result.errors)


def test_released_claim_does_not_block_worktree_reuse(tmp_path: Path):
    released = valid_claim_record()
    released["controller_id"] = "hermes-primary"
    released["lane_id"] = "pco-old"
    released["worktree_path"] = "/worktrees/reused"
    released["released_at"] = "2026-05-20T04:00:00Z"
    released["release_reason"] = "completed"

    live = valid_claim_record()
    live["controller_id"] = "nefarious-laptop-a"
    live["lane_id"] = "pco-new"
    live["worktree_path"] = "/worktrees/reused"

    _write_record(_claim_path(tmp_path, "hermes-primary", "pco-old"), released)
    _write_record(_claim_path(tmp_path, "nefarious-laptop-a", "pco-new"), live)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_lapsed_claim_does_not_block_worktree_reuse(tmp_path: Path):
    lapsed = valid_claim_record()
    lapsed["controller_id"] = "hermes-primary"
    lapsed["lane_id"] = "pco-old"
    lapsed["worktree_path"] = "/worktrees/reused"
    lapsed["released_at"] = "2026-05-20T04:00:00Z"
    lapsed["release_reason"] = "lapsed"

    live = valid_claim_record()
    live["controller_id"] = "nefarious-laptop-a"
    live["lane_id"] = "pco-new"
    live["worktree_path"] = "/worktrees/reused"

    _write_record(_claim_path(tmp_path, "hermes-primary", "pco-old"), lapsed)
    _write_record(_claim_path(tmp_path, "nefarious-laptop-a", "pco-new"), live)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_stale_unreleased_claim_warns_but_does_not_block_reuse(tmp_path: Path):
    stale = valid_claim_record()
    stale["controller_id"] = "hermes-primary"
    stale["lane_id"] = "pco-old"
    stale["worktree_path"] = "/worktrees/reused"
    stale["claimed_at"] = "2000-01-01T00:00:00Z"
    stale["last_heartbeat_at"] = "2000-01-01T00:00:00Z"
    stale["lease_seconds"] = 60

    live = valid_claim_record()
    live["controller_id"] = "nefarious-laptop-a"
    live["lane_id"] = "pco-new"
    live["worktree_path"] = "/worktrees/reused"

    _write_record(_claim_path(tmp_path, "hermes-primary", "pco-old"), stale)
    _write_record(_claim_path(tmp_path, "nefarious-laptop-a", "pco-new"), live)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]
    assert result.warnings
    assert any("stale" in warning.message for warning in result.warnings)


def test_heartbeat_claim_ref_must_resolve_to_claim(tmp_path: Path):
    heartbeat = valid_heartbeat_record()
    heartbeat["claim_ref"] = ".hermes/active-work-ledger/claims/hermes-primary/missing.yaml"
    _write_record(tmp_path / "heartbeats" / "hermes-primary" / "pco-slice0-author.yaml", heartbeat)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_HEARTBEAT_REF for error in result.errors)


def test_heartbeat_claim_ref_passes_when_claim_exists(tmp_path: Path):
    claim = valid_claim_record()
    claim_path = _claim_path(tmp_path, "hermes-primary", "pco-slice0-author")
    _write_record(claim_path, claim)

    heartbeat = valid_heartbeat_record()
    heartbeat["claim_ref"] = claim_path.relative_to(tmp_path).as_posix()
    _write_record(tmp_path / "heartbeats" / "hermes-primary" / "pco-slice0-author.yaml", heartbeat)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_event_subject_claim_ref_must_resolve_to_claim(tmp_path: Path):
    event = valid_event_record()
    event["subject_claim_ref"] = "claims/hermes-primary/missing.yaml"
    _write_record(tmp_path / "events" / "2026" / "05" / "20" / "event.yaml", event)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_EVENT_REF for error in result.errors)


def test_tmp_ledger_file_is_skipped_by_conflict_validator(tmp_path: Path):
    bad_claim = valid_claim_record()
    bad_claim["controller_id"] = "Bad_ID"
    _write_record(tmp_path / "claims" / "bad" / "claim.yaml.tmp.12345.abc", bad_claim)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


# ---------------------------------------------------------------------------
# Slice 2A — worktree-lease additive predicates
# ---------------------------------------------------------------------------


def valid_lease_record() -> dict:
    return {
        "kind": "worktree-lease-record",
        "record_type": "worktree_lease",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "pco-slice2a-author",
        "record_timestamp": "2026-05-21T03:08:08Z",
        "lease_id": "lease-pco-slice2a-001",
        "worktree_path": "/worktrees/pco-slice2a",
        "acquired_at": "2026-05-21T03:08:08Z",
        "lease_seconds": 3600,
        "expires_at": "9999-01-01T00:00:00Z",
    }


def test_slice2a_codes_registered():
    checks = registered_checks()
    assert CHECK_NAME in checks
    assert CODE_CLAIM_REQUIRES_LEASE in checks[CHECK_NAME].frs
    assert CODE_WORKTREE_LEASE_CONFLICT in checks[CHECK_NAME].frs
    assert CODE_LEASE_INVALID_RECORD in checks[CHECK_NAME].frs


def test_tree_with_zero_lease_records_preserves_slice1_behavior(tmp_path: Path):
    # Backward-compatibility floor: trees with no lease records continue
    # to validate identically to Slice 1/2. A live claim with no lease
    # present must NOT trigger PCO-021.
    claim = valid_claim_record()
    claim["controller_id"] = "hermes-primary"
    claim["lane_id"] = "pco-slice-a"
    claim["worktree_path"] = "/worktrees/pco-slice-a"
    _write_record(_claim_path(tmp_path, "hermes-primary", "pco-slice-a"), claim)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_live_claim_covered_by_live_lease_passes(tmp_path: Path):
    lease = valid_lease_record()
    lease["controller_id"] = "hermes-primary"
    lease["lane_id"] = "pco-slice-a"
    lease["worktree_path"] = "/worktrees/pco-slice-a"

    claim = valid_claim_record()
    claim["controller_id"] = "hermes-primary"
    claim["lane_id"] = "pco-slice-a"
    claim["worktree_path"] = "/worktrees/pco-slice-a"

    _write_record(tmp_path / "leases" / "hermes-primary" / "pco-slice-a.yaml", lease)
    _write_record(_claim_path(tmp_path, "hermes-primary", "pco-slice-a"), claim)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]


def test_live_claim_without_lease_fails_pco_021(tmp_path: Path):
    other_lease = valid_lease_record()
    other_lease["controller_id"] = "hermes-primary"
    other_lease["lane_id"] = "pco-other-lane"
    other_lease["lease_id"] = "lease-other-001"
    other_lease["worktree_path"] = "/worktrees/pco-other"
    _write_record(tmp_path / "leases" / "hermes-primary" / "pco-other.yaml", other_lease)

    claim = valid_claim_record()
    claim["controller_id"] = "hermes-primary"
    claim["lane_id"] = "pco-slice-a"
    claim["worktree_path"] = "/worktrees/pco-slice-a"
    _write_record(_claim_path(tmp_path, "hermes-primary", "pco-slice-a"), claim)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_CLAIM_REQUIRES_LEASE for error in result.errors)


def test_cross_controller_lease_conflict_fails_pco_022(tmp_path: Path):
    lease_a = valid_lease_record()
    lease_a["controller_id"] = "hermes-primary"
    lease_a["lane_id"] = "pco-slice-a"
    lease_a["lease_id"] = "lease-a-001"
    lease_a["worktree_path"] = "/worktrees/shared"

    lease_b = valid_lease_record()
    lease_b["controller_id"] = "nefarious-laptop-a"
    lease_b["lane_id"] = "pco-slice-b"
    lease_b["lease_id"] = "lease-b-001"
    lease_b["worktree_path"] = "/worktrees/shared/"

    _write_record(tmp_path / "leases" / "hermes-primary" / "pco-slice-a.yaml", lease_a)
    _write_record(tmp_path / "leases" / "nefarious-laptop-a" / "pco-slice-b.yaml", lease_b)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_WORKTREE_LEASE_CONFLICT for error in result.errors)
    assert any("/worktrees/shared" in error.message for error in result.errors)


def test_expired_lease_no_longer_covers_claim_fails_pco_021(tmp_path: Path):
    expired_lease = valid_lease_record()
    expired_lease["controller_id"] = "hermes-primary"
    expired_lease["lane_id"] = "pco-slice-a"
    expired_lease["lease_id"] = "lease-expired-001"
    expired_lease["worktree_path"] = "/worktrees/pco-slice-a"
    expired_lease["acquired_at"] = "2000-01-01T00:00:00Z"
    expired_lease["expires_at"] = "2000-01-02T00:00:00Z"

    claim = valid_claim_record()
    claim["controller_id"] = "hermes-primary"
    claim["lane_id"] = "pco-slice-a"
    claim["worktree_path"] = "/worktrees/pco-slice-a"

    _write_record(tmp_path / "leases" / "hermes-primary" / "pco-slice-a.yaml", expired_lease)
    _write_record(_claim_path(tmp_path, "hermes-primary", "pco-slice-a"), claim)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_CLAIM_REQUIRES_LEASE for error in result.errors)


def test_same_controller_mismatched_lane_still_covers_worktree(tmp_path: Path):
    # Lease covers worktree, not lane. Lane uniqueness is owned by
    # PCO-016. A same-controller lease whose lane_id differs from the
    # claim's lane_id must still satisfy PCO-021 because the worktree
    # is covered under the same controller.
    lease = valid_lease_record()
    lease["controller_id"] = "hermes-primary"
    lease["lane_id"] = "pco-slice-a-planner"
    lease["lease_id"] = "lease-pco-slice-a-planner"
    lease["worktree_path"] = "/worktrees/pco-slice-a"

    claim = valid_claim_record()
    claim["controller_id"] = "hermes-primary"
    claim["lane_id"] = "pco-slice-a"
    claim["worktree_path"] = "/worktrees/pco-slice-a"

    _write_record(tmp_path / "leases" / "hermes-primary" / "planner.yaml", lease)
    _write_record(_claim_path(tmp_path, "hermes-primary", "pco-slice-a"), claim)

    result = run([tmp_path])

    assert not any(
        error.code == CODE_CLAIM_REQUIRES_LEASE for error in result.errors
    ), [error.format() for error in result.errors]


def test_cross_controller_claim_under_other_controllers_lease_fails(tmp_path: Path):
    # A live lease held by controller A does NOT cover a claim by
    # controller B on the same worktree; PCO-021 must fire on B's claim
    # (and PCO-022 would fire only if B also held its own live lease).
    lease_a = valid_lease_record()
    lease_a["controller_id"] = "hermes-primary"
    lease_a["lane_id"] = "pco-slice-a"
    lease_a["lease_id"] = "lease-a-001"
    lease_a["worktree_path"] = "/worktrees/pco-slice-a"

    claim_b = valid_claim_record()
    claim_b["controller_id"] = "nefarious-laptop-a"
    claim_b["lane_id"] = "pco-slice-b"
    claim_b["worktree_path"] = "/worktrees/pco-slice-a"

    _write_record(tmp_path / "leases" / "hermes-primary" / "pco-slice-a.yaml", lease_a)
    _write_record(_claim_path(tmp_path, "nefarious-laptop-a", "pco-slice-b"), claim_b)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_CLAIM_REQUIRES_LEASE for error in result.errors)


def test_malformed_lease_record_in_conflict_scan_emits_pco_023(tmp_path: Path):
    bad_lease = valid_lease_record()
    bad_lease["controller_id"] = "Bad_ID"
    _write_record(tmp_path / "leases" / "bad.yaml", bad_lease)

    result = run([tmp_path])

    assert not result.ok
    assert any(error.code == CODE_LEASE_INVALID_RECORD for error in result.errors)


def test_tmp_lease_file_is_skipped_by_conflict_validator(tmp_path: Path):
    bad_lease = valid_lease_record()
    bad_lease["controller_id"] = "Bad_ID"
    _write_record(tmp_path / "leases" / "bad" / "lease.yaml.tmp.12345.abc", bad_lease)

    result = run([tmp_path])

    assert result.ok, [error.format() for error in result.errors]
