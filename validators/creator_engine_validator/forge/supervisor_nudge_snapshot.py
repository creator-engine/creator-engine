"""Pure supervisor-nudge proposal classification from injected facts.

This snapshot is deliberately a read-model helper.  It does not discover
facts, read state, start validators, or dispatch seats.  A caller supplies
typed observations and may decide separately whether any proposal warrants an
operator action.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProposalKind(str, Enum):
    """The bounded, non-actuating classes a supervisor may surface."""

    STALE_REVIEW_HEAD = "stale_review_head"
    IDLE_SEAT_RESTOCK = "idle_seat_restock"
    DUPLICATE_WORK = "duplicate_work"
    DUPLICATE_VALIDATOR = "duplicate_validator"
    PREFLIGHT_CAPACITY = "preflight_capacity"
    QUEUE_LIMBO = "queue_limbo"
    WATCHER_COVERAGE_GAP = "watcher_coverage_gap"
    CONTEXT_CHECKPOINT = "context_checkpoint"


@dataclass(frozen=True)
class SupervisorProposal:
    """One deterministic proposal; it is not an instruction or side effect."""

    kind: ProposalKind
    subject: str


@dataclass(frozen=True)
class ReviewHeadFact:
    review_id: str
    approved_head: str
    current_head: str


@dataclass(frozen=True)
class IdleSeatFact:
    seat_id: str
    state: str
    unchanged_polls: int
    restock_after_polls: int


@dataclass(frozen=True)
class DuplicateFact:
    subject: str
    category: str
    active_count: int


@dataclass(frozen=True)
class PreflightCapacityFact:
    capacity_id: str
    free_bytes: int
    required_bytes: int


@dataclass(frozen=True)
class QueueLimboFact:
    item_id: str
    observed_passes: int
    limbo_after_passes: int


@dataclass(frozen=True)
class CoverageFact:
    seat_id: str
    watcher_seen: bool
    seat_seen: bool


@dataclass(frozen=True)
class ContextCheckpointFact:
    checkpoint_id: str
    context_percent: int
    checkpoint_percent: int


@dataclass(frozen=True)
class SupervisorFacts:
    """All observations are injected; no clock, process, or filesystem is read."""

    reviews: tuple[ReviewHeadFact, ...] = ()
    idle_seats: tuple[IdleSeatFact, ...] = ()
    duplicates: tuple[DuplicateFact, ...] = ()
    capacities: tuple[PreflightCapacityFact, ...] = ()
    queue_limbo: tuple[QueueLimboFact, ...] = ()
    coverage: tuple[CoverageFact, ...] = ()
    checkpoints: tuple[ContextCheckpointFact, ...] = ()


def classify_supervisor_facts(facts: SupervisorFacts | object) -> tuple[SupervisorProposal, ...]:
    """Return sorted, deduplicated proposals, or no proposals for bad facts.

    Failing closed is intentional: a partially malformed snapshot must not
    cause a supervisor action from the remaining observations.
    """

    if not _valid_facts(facts):
        return ()
    assert isinstance(facts, SupervisorFacts)

    proposals: set[SupervisorProposal] = set()
    for fact in facts.reviews:
        if fact.approved_head != fact.current_head:
            proposals.add(SupervisorProposal(ProposalKind.STALE_REVIEW_HEAD, fact.review_id))
    for fact in facts.idle_seats:
        if fact.state == "idle" and fact.unchanged_polls >= fact.restock_after_polls:
            proposals.add(SupervisorProposal(ProposalKind.IDLE_SEAT_RESTOCK, fact.seat_id))
    for fact in facts.duplicates:
        if fact.active_count >= 2:
            kind = (
                ProposalKind.DUPLICATE_WORK
                if fact.category == "work"
                else ProposalKind.DUPLICATE_VALIDATOR
            )
            proposals.add(SupervisorProposal(kind, fact.subject))
    for fact in facts.capacities:
        if fact.free_bytes < fact.required_bytes:
            proposals.add(SupervisorProposal(ProposalKind.PREFLIGHT_CAPACITY, fact.capacity_id))
    for fact in facts.queue_limbo:
        if fact.observed_passes >= fact.limbo_after_passes:
            proposals.add(SupervisorProposal(ProposalKind.QUEUE_LIMBO, fact.item_id))
    for fact in facts.coverage:
        if not fact.watcher_seen or not fact.seat_seen:
            proposals.add(SupervisorProposal(ProposalKind.WATCHER_COVERAGE_GAP, fact.seat_id))
    for fact in facts.checkpoints:
        if fact.context_percent >= fact.checkpoint_percent:
            proposals.add(SupervisorProposal(ProposalKind.CONTEXT_CHECKPOINT, fact.checkpoint_id))
    return tuple(sorted(proposals, key=lambda proposal: (proposal.kind.value, proposal.subject)))


def _valid_facts(facts: object) -> bool:
    if not isinstance(facts, SupervisorFacts):
        return False
    return (
        _valid_reviews(facts.reviews)
        and _valid_idle_seats(facts.idle_seats)
        and _valid_duplicates(facts.duplicates)
        and _valid_capacities(facts.capacities)
        and _valid_queue_limbo(facts.queue_limbo)
        and _valid_coverage(facts.coverage)
        and _valid_checkpoints(facts.checkpoints)
    )


def _text(value: object) -> bool:
    return type(value) is str and bool(value)


def _positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def _nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _valid_reviews(facts: object) -> bool:
    return type(facts) is tuple and all(
        isinstance(fact, ReviewHeadFact)
        and _text(fact.review_id)
        and _text(fact.approved_head)
        and _text(fact.current_head)
        for fact in facts
    )


def _valid_idle_seats(facts: object) -> bool:
    return type(facts) is tuple and all(
        isinstance(fact, IdleSeatFact)
        and _text(fact.seat_id)
        and fact.state in {"idle", "working", "down"}
        and _nonnegative_int(fact.unchanged_polls)
        and _positive_int(fact.restock_after_polls)
        for fact in facts
    )


def _valid_duplicates(facts: object) -> bool:
    return type(facts) is tuple and all(
        isinstance(fact, DuplicateFact)
        and _text(fact.subject)
        and fact.category in {"work", "validator"}
        and _positive_int(fact.active_count)
        for fact in facts
    )


def _valid_capacities(facts: object) -> bool:
    return type(facts) is tuple and all(
        isinstance(fact, PreflightCapacityFact)
        and _text(fact.capacity_id)
        and _nonnegative_int(fact.free_bytes)
        and _positive_int(fact.required_bytes)
        for fact in facts
    )


def _valid_queue_limbo(facts: object) -> bool:
    return type(facts) is tuple and all(
        isinstance(fact, QueueLimboFact)
        and _text(fact.item_id)
        and _nonnegative_int(fact.observed_passes)
        and _positive_int(fact.limbo_after_passes)
        for fact in facts
    )


def _valid_coverage(facts: object) -> bool:
    return type(facts) is tuple and all(
        isinstance(fact, CoverageFact)
        and _text(fact.seat_id)
        and type(fact.watcher_seen) is bool
        and type(fact.seat_seen) is bool
        for fact in facts
    )


def _valid_checkpoints(facts: object) -> bool:
    return type(facts) is tuple and all(
        isinstance(fact, ContextCheckpointFact)
        and _text(fact.checkpoint_id)
        and _nonnegative_int(fact.context_percent)
        and _nonnegative_int(fact.checkpoint_percent)
        and fact.context_percent <= 100
        and fact.checkpoint_percent <= 100
        for fact in facts
    )
