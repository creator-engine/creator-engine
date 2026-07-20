"""CE603 raw-token work-unit policy facade and advisory binding.

Receipt serialization, validation, and projection live in
``work_unit_ledger`` so v1 ledger I/O and this runner can consume the same
neutral substrate.  Per the verified DEV2 2026-07-19 ruling,
``VerifiedCurrentWorkUnitBinding`` is advisory misuse-resistance only: no
authority depends on same-interpreter unforgeability.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .. import work_unit_ledger as ledger

UNIT = ledger.UNIT
UNIT_VERSION = ledger.UNIT_VERSION
PHASES = ledger.PHASES
SOURCE_STATES = ledger.SOURCE_STATES
GENESIS_RECEIPT_SHA256 = ledger.GENESIS_RECEIPT_SHA256
WorkUnitProjection = ledger.WorkUnitProjection
_canonical_bytes = ledger.canonical_json_bytes
receipt_sha256 = ledger.receipt_sha256
_is_count = ledger.is_count
_receipt_id = ledger.receipt_id
_make_receipt = ledger.make_receipt
validate_receipts = ledger.validate_receipts
project = ledger.project
_IDENTIFIER_RE = ledger.IDENTIFIER_RE


@dataclass(frozen=True)
class WorkUnitDecision:
    allowed: bool
    reason: str
    receipt: dict[str, Any]
    persist: bool = True
    binding: object | None = None


class VerifiedCurrentWorkUnitBinding:
    """An advisory, unwired in-process binding, not a security capability or act authority.

    The DEV2 2026-07-19 ruling records that same-interpreter code may forge
    this object through ``object.__getattribute__`` and
    ``object.__setattr__``.  It only guards against accidental copying and
    misuse; durable act predicates must verify their own evidence. This seam
    does not enforce production dispatch.
    """

    __slots__ = ("__ce603_issuance",)

    def __new__(cls, *args: object, **kwargs: object):
        raise TypeError("work-unit bindings are issued by runner policy only")

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("work-unit bindings cannot be subclassed")

    def __copy__(self):
        raise TypeError("work-unit bindings cannot be copied")

    def __deepcopy__(self, memo: dict[int, object]):
        raise TypeError("work-unit bindings cannot be copied")

    def __reduce__(self):
        raise TypeError("work-unit bindings cannot be serialized")

    def __reduce_ex__(self, protocol: int):
        raise TypeError("work-unit bindings cannot be serialized")


def issue_advisory_binding(context: tuple[object, ...]) -> VerifiedCurrentWorkUnitBinding:
    """Create a copy-resistant advisory handle for already-verified context."""
    binding = object.__new__(VerifiedCurrentWorkUnitBinding)

    def issued_context(candidate: object) -> tuple[object, ...] | None:
        return context if candidate is binding else None

    object.__setattr__(binding, "_VerifiedCurrentWorkUnitBinding__ce603_issuance", issued_context)
    return binding


def advisory_binding_context(binding: object) -> tuple[object, ...] | None:
    """Return advisory context only; callers must not treat it as authority."""
    if type(binding) is not VerifiedCurrentWorkUnitBinding:
        return None
    try:
        verifier = object.__getattribute__(binding, "_VerifiedCurrentWorkUnitBinding__ce603_issuance")
        context = verifier(binding) if callable(verifier) else None
    except (AttributeError, TypeError):
        return None
    return context if isinstance(context, tuple) else None


def advisory_binding_matches(binding: object, expected: tuple[object, ...]) -> bool:
    """Compare advisory context; this result conveys no independent authority."""
    return advisory_binding_context(binding) == expected


def reserve(
    receipts: Iterable[Mapping[str, Any]],
    *,
    cap: int,
    run_id: str,
    attempt_id: str,
    reservation_id: str,
    requested: int,
    policy_sha256: str,
    recorded_at: str,
) -> WorkUnitDecision:
    """Reserve raw-token units exactly once for a run, before dispatch."""
    if not _is_count(requested) or requested <= 0:
        raise ValueError("requested must be a positive integer")
    stream = tuple(receipts)
    projection = project(stream, cap=cap, run_id=run_id)
    reservation_history = [
        receipt for receipt in stream
        if isinstance(receipt, Mapping) and receipt.get("run_id") == run_id
        and receipt.get("reservation_id") == reservation_id
    ]
    if reservation_history:
        latest = reservation_history[-1]
        if not projection.safe or validate_receipts(stream):
            return WorkUnitDecision(False, "work_unit_receipts_invalid", dict(latest), persist=False)
        if latest.get("phase") in {"completion", "rollback"}:
            return WorkUnitDecision(False, "work_unit_retry_reservation_terminal", dict(latest), persist=False)
        invariant_fields = {"reserved": requested, "policy_sha256": policy_sha256, "cap": cap}
        if not isinstance(attempt_id, str) or not _IDENTIFIER_RE.fullmatch(attempt_id):
            return WorkUnitDecision(False, "work_unit_retry_invariant_invalid", dict(latest), persist=False)
        if latest.get("attempt_id") != attempt_id or latest.get("phase") not in {"pre_dispatch", "mid_run"} or any(
            latest.get(name) != value for name, value in invariant_fields.items()
        ):
            return WorkUnitDecision(False, "work_unit_retry_invariant_invalid", dict(latest), persist=False)
        return WorkUnitDecision(True, "work_unit_reservation_reused", dict(latest), persist=False)
    remaining = projection.remaining - requested
    predecessor = projection.last_receipt.get("receipt_sha256") if projection.last_receipt else GENESIS_RECEIPT_SHA256
    receipt = _make_receipt(
        run_id=run_id, attempt_id=attempt_id, reservation_id=reservation_id, phase="pre_dispatch", cap=cap,
        reserved=requested, observed=0, remaining=max(remaining, 0), sample_sequence=0,
        source_state="measured" if projection.safe and remaining >= 0 else "unknown",
        policy_sha256=policy_sha256, previous_receipt_sha256=str(predecessor), recorded_at=recorded_at,
    )
    if not projection.safe:
        return WorkUnitDecision(False, "work_unit_receipts_invalid", receipt, persist=False)
    if remaining < 0:
        return WorkUnitDecision(False, "work_unit_cap_exhausted", receipt, persist=False)
    return WorkUnitDecision(True, "work_unit_reserved", receipt)


def reconcile(
    receipts: Iterable[Mapping[str, Any]],
    *,
    cap: int,
    run_id: str,
    attempt_id: str,
    reservation_id: str,
    sample_sequence: int,
    observed: int,
    policy_sha256: str,
    recorded_at: str,
) -> WorkUnitDecision:
    """Reconcile a monotonic usage sample; gaps and malformed values block turns."""
    if not _is_count(sample_sequence) or not _is_count(observed):
        raise ValueError("sample sequence and observed units must be non-negative integers")
    stream = tuple(receipts)
    projection = project(stream, cap=cap, run_id=run_id)
    receipt_errors = validate_receipts(stream)
    reservation_history = [receipt for receipt in stream if isinstance(receipt, Mapping) and receipt.get("run_id") == run_id and receipt.get("reservation_id") == reservation_id]
    prior = reservation_history[-1] if reservation_history else None
    if prior is None or prior.get("phase") not in {"pre_dispatch", "mid_run"}:
        receipt = _make_receipt(run_id=run_id, attempt_id=attempt_id, reservation_id=reservation_id, phase="reconcile", cap=cap, reserved=0, observed=observed, remaining=0, sample_sequence=sample_sequence, source_state="unknown", policy_sha256=policy_sha256, previous_receipt_sha256=GENESIS_RECEIPT_SHA256, recorded_at=recorded_at)
        return WorkUnitDecision(False, "work_unit_reservation_missing", receipt, persist=False)
    if prior.get("attempt_id") != attempt_id or prior.get("policy_sha256") != policy_sha256:
        return WorkUnitDecision(False, "work_unit_reservation_identity_mismatch", dict(prior), persist=False)
    if receipt_errors:
        return WorkUnitDecision(False, "work_unit_receipts_invalid", dict(prior), persist=False)
    prior_sequence = int(prior["sample_sequence"])
    prior_observed = int(prior["observed"])
    if sample_sequence == prior_sequence and observed == prior_observed:
        return WorkUnitDecision(projection.safe, "work_unit_sample_replayed", dict(prior), persist=False)
    if sample_sequence <= prior_sequence:
        return WorkUnitDecision(False, "work_unit_sample_replayed_conflict", dict(prior), persist=False)
    predecessor = str(projection.last_receipt["receipt_sha256"]) if projection.last_receipt else GENESIS_RECEIPT_SHA256
    reserved = int(prior["reserved"])
    successor_attempt_id = str(prior["attempt_id"])
    successor_policy_sha256 = str(prior["policy_sha256"])
    if observed < prior_observed:
        receipt = _make_receipt(run_id=run_id, attempt_id=successor_attempt_id, reservation_id=reservation_id, phase="mid_run", cap=cap, reserved=reserved, observed=observed, remaining=max(projection.remaining, 0), sample_sequence=sample_sequence, source_state="unknown", policy_sha256=successor_policy_sha256, previous_receipt_sha256=predecessor, recorded_at=recorded_at)
        return WorkUnitDecision(False, "work_unit_observed_decreased", receipt, persist=False)
    source_state = "measured" if projection.safe and sample_sequence == prior_sequence + 1 and observed <= reserved else "unknown"
    receipt = _make_receipt(run_id=run_id, attempt_id=successor_attempt_id, reservation_id=reservation_id, phase="mid_run", cap=cap, reserved=reserved, observed=observed, remaining=max(cap - projection.committed - projection.live_reservations, 0), sample_sequence=sample_sequence, source_state=source_state, policy_sha256=successor_policy_sha256, previous_receipt_sha256=predecessor, recorded_at=recorded_at)
    if source_state != "measured":
        return WorkUnitDecision(False, "work_unit_sample_unknown", receipt)
    return WorkUnitDecision(True, "work_unit_reconciled", receipt)


def _terminal(
    receipts: Iterable[Mapping[str, Any]], *, phase: str, cap: int, run_id: str, attempt_id: str,
    reservation_id: str, observed: int | None, policy_sha256: str, recorded_at: str,
) -> WorkUnitDecision:
    stream = tuple(receipts)
    projection = project(stream, cap=cap, run_id=run_id)
    receipt_errors = validate_receipts(stream)
    history = [receipt for receipt in stream if isinstance(receipt, Mapping) and receipt.get("run_id") == run_id and receipt.get("reservation_id") == reservation_id]
    prior = history[-1] if history else None
    if prior is None or prior.get("phase") not in {"pre_dispatch", "mid_run"}:
        receipt = _make_receipt(run_id=run_id, attempt_id=attempt_id, reservation_id=reservation_id, phase=phase, cap=cap, reserved=0, observed=0, remaining=max(projection.remaining, 0), sample_sequence=0, source_state="unknown", policy_sha256=policy_sha256, previous_receipt_sha256=GENESIS_RECEIPT_SHA256, recorded_at=recorded_at)
        return WorkUnitDecision(False, "work_unit_reservation_missing", receipt, persist=False)
    if prior.get("attempt_id") != attempt_id or prior.get("policy_sha256") != policy_sha256:
        return WorkUnitDecision(False, "work_unit_reservation_identity_mismatch", dict(prior), persist=False)
    if receipt_errors:
        return WorkUnitDecision(False, "work_unit_receipts_invalid", dict(prior), persist=False)
    reserved = int(prior["reserved"])
    successor_attempt_id = str(prior["attempt_id"])
    successor_policy_sha256 = str(prior["policy_sha256"])
    prior_observed = int(prior["observed"])
    final_observed = prior_observed if observed is None else observed
    if not _is_count(final_observed) or not prior_observed <= final_observed <= reserved:
        return WorkUnitDecision(False, "work_unit_terminal_observed_invalid", dict(prior), persist=False)
    sequence = int(prior["sample_sequence"]) + (1 if phase == "completion" else 0)
    successor_remaining = projection.remaining + reserved - (final_observed if phase == "completion" else 0)
    predecessor = str(projection.last_receipt["receipt_sha256"]) if projection.last_receipt else GENESIS_RECEIPT_SHA256
    receipt = _make_receipt(run_id=run_id, attempt_id=successor_attempt_id, reservation_id=reservation_id, phase=phase, cap=cap, reserved=reserved, observed=final_observed, remaining=successor_remaining, sample_sequence=sequence, source_state="measured" if projection.safe else "unknown", policy_sha256=successor_policy_sha256, previous_receipt_sha256=predecessor, recorded_at=recorded_at)
    return WorkUnitDecision(projection.safe, f"work_unit_{phase}", receipt)


def complete(receipts: Iterable[Mapping[str, Any]], *, cap: int, run_id: str, attempt_id: str, reservation_id: str, observed: int, policy_sha256: str, recorded_at: str) -> WorkUnitDecision:
    """Commit a reservation's measured usage exactly once."""
    return _terminal(receipts, phase="completion", cap=cap, run_id=run_id, attempt_id=attempt_id, reservation_id=reservation_id, observed=observed, policy_sha256=policy_sha256, recorded_at=recorded_at)


def rollback(receipts: Iterable[Mapping[str, Any]], *, cap: int, run_id: str, attempt_id: str, reservation_id: str, policy_sha256: str, recorded_at: str) -> WorkUnitDecision:
    """Release an uncommitted reservation while preserving its observed sample."""
    return _terminal(receipts, phase="rollback", cap=cap, run_id=run_id, attempt_id=attempt_id, reservation_id=reservation_id, observed=None, policy_sha256=policy_sha256, recorded_at=recorded_at)
