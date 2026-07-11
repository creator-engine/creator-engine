"""Pure gate-ready ratifier queue state derived from injected facts.

The queue neither discovers pull requests nor runs validation.  Its caller
owns observation, persistence, and any key-holder transport; this module only
orders candidates and reduces their supplied attestation evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Iterable
from typing import Literal

from .ready_attestation_nudge import ReadyAttestationFacts, reduce_ready_attestation


SUPERSEDES = "crons:23:53"

QueueStatus = Literal["PENDING", "ATTESTED", "STALE", "BLOCKED"]


@dataclass(frozen=True)
class RatifierCandidate:
    """Persistent, caller-owned state for one gate-ready pull-request head."""

    pr_number: int
    head_sha: str
    branch: str
    enqueued_at: str
    attestation_state: str
    last_checked_at: str | None
    checked_count: int


@dataclass(frozen=True)
class RatifierQueueEntry:
    """One candidate's derived queue status and non-actuating explanation."""

    candidate: RatifierCandidate
    status: QueueStatus
    reason: str


@dataclass(frozen=True)
class RatifierQueueState:
    """Oldest-first, derived state for a complete ratifier queue snapshot."""

    entries: tuple[RatifierQueueEntry, ...]

    @property
    def candidates(self) -> tuple[RatifierCandidate, ...]:
        """Return the same oldest-first candidates without losing entry detail."""

        return tuple(entry.candidate for entry in self.entries)


def compute_queue_state(candidates: Iterable[RatifierCandidate]) -> RatifierQueueState:
    """Return an oldest-first pure queue snapshot.

    A mismatched validation SHA is stale evidence, not a terminal block: a
    caller can inject fresh facts for the candidate's current head next pass.
    Failed or unrecognized evidence fails closed as ``BLOCKED``.
    """

    ordered = sorted(candidates, key=lambda candidate: candidate.enqueued_at)
    return RatifierQueueState(
        tuple(
            RatifierQueueEntry(candidate, *_status_for(candidate.attestation_state))
            for candidate in ordered
        )
    )


def drive_attestation(
    candidate: RatifierCandidate, facts: ReadyAttestationFacts
) -> RatifierCandidate:
    """Apply one injected attestation proposal without observing time or I/O.

    The facts reducer owns validation semantics.  This queue layer records the
    resulting state and pass count only; ``last_checked_at`` remains caller
    owned because this pure API receives no clock observation.
    """

    proposal = reduce_ready_attestation(facts)
    return replace(
        candidate,
        attestation_state=proposal.state,
        checked_count=candidate.checked_count + 1,
    )


def render_queue(queue_state: RatifierQueueState) -> str:
    """Render a compact, human-readable key-holder queue summary."""

    entries = queue_state.entries
    attested = tuple(entry for entry in entries if entry.status == "ATTESTED")
    lines = [
        f"Ratifier queue: {len(entries)} candidate(s); {len(attested)} ATTESTED.",
    ]
    if entries:
        first = entries[0]
        candidate = first.candidate
        lines.append(
            "Highest priority: "
            f"PR #{candidate.pr_number} ({candidate.branch}, {candidate.head_sha}) "
            f"is {first.status}."
        )
    for entry in entries:
        if entry.status == "BLOCKED":
            lines.append(f"BLOCKED PR #{entry.candidate.pr_number}: {entry.reason}.")
    return "\n".join(lines)


def _status_for(attestation_state: str) -> tuple[QueueStatus, str]:
    if attestation_state == "attested_green":
        return "ATTESTED", "terminal_green_evidence"
    if attestation_state == "sha_mismatch":
        return "STALE", "validation_sha_differs_from_ready_sha"
    if attestation_state == "validator_live":
        return "PENDING", "validator_is_live"
    if attestation_state == "pending":
        return "PENDING", "validation_not_started"
    if attestation_state == "failed":
        return "BLOCKED", "attestation_failed"
    return "BLOCKED", "unrecognized_attestation_state"
