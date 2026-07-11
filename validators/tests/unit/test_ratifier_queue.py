"""Tests for the pure, injected-facts ratifier queue."""
from __future__ import annotations

from creator_engine_validator.forge import ratifier_queue as queue
from creator_engine_validator.forge.ready_attestation_nudge import ReadyAttestationFacts


_SHA = "a" * 40
_OTHER_SHA = "b" * 40


def _candidate(number: int, *, state: str = "pending", enqueued_at: str = "2026-07-11T00:00:00Z"):
    return queue.RatifierCandidate(
        pr_number=number,
        head_sha=_SHA,
        branch=f"feature/{number}",
        enqueued_at=enqueued_at,
        attestation_state=state,
        last_checked_at=None,
        checked_count=0,
    )


def test_compute_queue_state_orders_mixed_candidates_and_derives_statuses():
    state = queue.compute_queue_state(
        (
            _candidate(4, state="failed", enqueued_at="2026-07-11T04:00:00Z"),
            _candidate(2, state="attested_green", enqueued_at="2026-07-11T02:00:00Z"),
            _candidate(3, state="sha_mismatch", enqueued_at="2026-07-11T03:00:00Z"),
            _candidate(1, state="validator_live", enqueued_at="2026-07-11T01:00:00Z"),
        )
    )

    assert [entry.candidate.pr_number for entry in state.entries] == [1, 2, 3, 4]
    assert [entry.status for entry in state.entries] == ["PENDING", "ATTESTED", "STALE", "BLOCKED"]
    assert state.entries[-1].reason == "attestation_failed"


def test_drive_attestation_round_trip_delegates_to_ready_attestation_reducer():
    candidate = _candidate(7, state="pending")
    updated = queue.drive_attestation(
        candidate,
        ReadyAttestationFacts(
            ready_sha=_SHA,
            validation_sha=_SHA,
            exit_code=0,
            structural_failures=0,
            environment_failures=0,
        ),
    )

    assert updated.attestation_state == "attested_green"
    assert updated.checked_count == 1
    assert updated.last_checked_at is None
    assert candidate.checked_count == 0
    assert queue.compute_queue_state((updated,)).entries[0].status == "ATTESTED"


def test_render_queue_includes_attested_count_priority_and_blocked_reason():
    state = queue.compute_queue_state(
        (
            _candidate(12, state="failed", enqueued_at="2026-07-11T01:00:00Z"),
            _candidate(13, state="attested_green", enqueued_at="2026-07-11T02:00:00Z"),
        )
    )

    rendered = queue.render_queue(state)
    assert "1 ATTESTED" in rendered
    assert "Highest priority: PR #12" in rendered
    assert "BLOCKED PR #12: attestation_failed" in rendered


def test_supersedes_is_the_machine_readable_cron_retirement_marker():
    assert queue.SUPERSEDES == "crons:23:53"


def test_unknown_attestation_evidence_fails_closed_and_module_has_no_io_surface():
    state = queue.compute_queue_state((_candidate(14, state="not-a-state"),))
    assert state.entries[0].status == "BLOCKED"
    assert state.entries[0].reason == "unrecognized_attestation_state"
    forbidden = {"subprocess", "socket", "requests", "urllib", "os", "pathlib", "queue", "gh"}
    assert forbidden.isdisjoint(vars(queue))
