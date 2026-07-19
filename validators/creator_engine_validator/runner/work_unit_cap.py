"""Pure CE603 raw-token work-unit-cap policy and receipt projection."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

UNIT = "ce.raw_tokens.v1"
UNIT_VERSION = 1
PHASES = frozenset({"pre_dispatch", "mid_run", "completion", "rollback", "reconcile"})
SOURCE_STATES = frozenset({"measured", "unknown", "late", "replayed"})
GENESIS_RECEIPT_SHA256 = "0" * 64
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


@dataclass(frozen=True)
class WorkUnitDecision:
    allowed: bool
    reason: str
    receipt: dict[str, Any]
    persist: bool = True
    binding: object | None = None


@dataclass(frozen=True)
class WorkUnitProjection:
    committed: int
    live_reservations: int
    remaining: int
    safe: bool
    last_sequence: int
    last_receipt: dict[str, Any] | None


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    """Match the side-effect ledger's sorted-key, UTF-8, newline format."""
    return (json.dumps(dict(value), sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def receipt_sha256(receipt: Mapping[str, Any]) -> str:
    material = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return hashlib.sha256(_canonical_bytes(material)).hexdigest()


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _receipt_id(material: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(material)).hexdigest()


def _make_receipt(
    *,
    run_id: str,
    attempt_id: str,
    reservation_id: str,
    phase: str,
    cap: int,
    reserved: int,
    observed: int,
    remaining: int,
    sample_sequence: int,
    source_state: str,
    policy_sha256: str,
    previous_receipt_sha256: str,
    recorded_at: str,
) -> dict[str, Any]:
    if phase not in PHASES or source_state not in SOURCE_STATES:
        raise ValueError("unknown CE603 receipt vocabulary")
    values = (cap, reserved, observed, remaining, sample_sequence)
    if not all(_is_count(value) for value in values):
        raise ValueError("CE603 receipt amounts must be non-negative integers")
    identity = {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "reservation_id": reservation_id,
        "phase": phase,
        "sample_sequence": sample_sequence,
        "previous_receipt_sha256": previous_receipt_sha256,
    }
    receipt: dict[str, Any] = {
        "receipt_id": _receipt_id(identity),
        "run_id": run_id,
        "attempt_id": attempt_id,
        "reservation_id": reservation_id,
        "phase": phase,
        "unit": UNIT,
        "unit_version": UNIT_VERSION,
        "cap": cap,
        "reserved": reserved,
        "observed": observed,
        "remaining": remaining,
        "sample_sequence": sample_sequence,
        "source_state": source_state,
        "policy_sha256": policy_sha256,
        "previous_receipt_sha256": previous_receipt_sha256,
        "recorded_at": recorded_at,
    }
    receipt["receipt_sha256"] = receipt_sha256(receipt)
    return receipt


def validate_receipts(receipts: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """Validate the closed, chained, arithmetic CE603 receipt contract."""
    errors: list[str] = []
    prior_by_run: dict[str, str] = {}
    state_by_run: dict[str, dict[str, Any]] = {}
    required = {
        "receipt_id", "run_id", "attempt_id", "reservation_id", "phase", "unit", "unit_version",
        "cap", "reserved", "observed", "remaining", "sample_sequence", "source_state",
        "policy_sha256", "previous_receipt_sha256", "receipt_sha256", "recorded_at",
    }
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            errors.append("receipt_not_mapping")
            continue
        if set(receipt) != required:
            errors.append("receipt_shape_invalid")
            continue
        strings = ("run_id", "attempt_id", "reservation_id")
        if not all(isinstance(receipt.get(name), str) and _IDENTIFIER_RE.fullmatch(receipt[name]) for name in strings):
            errors.append("receipt_identifier_invalid")
            continue
        if not isinstance(receipt.get("recorded_at"), str) or not receipt["recorded_at"]:
            errors.append("receipt_recorded_at_invalid")
            continue
        if not all(isinstance(receipt.get(name), str) and _SHA256_RE.fullmatch(receipt[name]) for name in ("policy_sha256", "previous_receipt_sha256", "receipt_sha256", "receipt_id")):
            errors.append("receipt_hash_invalid")
            continue
        identity = {name: receipt[name] for name in ("run_id", "attempt_id", "reservation_id", "phase", "sample_sequence", "previous_receipt_sha256")}
        if receipt["receipt_id"] != _receipt_id(identity):
            errors.append("receipt_id_invalid")
        if receipt.get("unit") != UNIT or receipt.get("unit_version") != UNIT_VERSION:
            errors.append("receipt_unit_invalid")
        if receipt.get("phase") not in PHASES or receipt.get("source_state") not in SOURCE_STATES:
            errors.append("receipt_vocabulary_invalid")
        if not all(_is_count(receipt.get(name)) for name in ("cap", "reserved", "observed", "remaining", "sample_sequence")):
            errors.append("receipt_amount_invalid")
            continue
        if receipt.get("receipt_sha256") != receipt_sha256(receipt):
            errors.append("receipt_digest_invalid")
        run_id = receipt["run_id"]
        expected = prior_by_run.get(run_id, GENESIS_RECEIPT_SHA256)
        if receipt["previous_receipt_sha256"] != expected:
            errors.append("receipt_predecessor_invalid")
        prior_by_run[run_id] = receipt["receipt_sha256"]

        run = state_by_run.setdefault(run_id, {"cap": receipt["cap"], "committed": 0, "reservations": {}})
        if run["cap"] != receipt["cap"]:
            errors.append("receipt_cap_invalid")
            continue
        reservations: dict[str, dict[str, Any]] = run["reservations"]
        reservation_id = receipt["reservation_id"]
        phase = receipt["phase"]
        expected_remaining: int | None = None
        if phase == "pre_dispatch":
            if reservation_id in reservations or receipt["sample_sequence"] != 0 or receipt["observed"] != 0 or receipt["reserved"] <= 0:
                errors.append("receipt_phase_invalid")
                continue
            reservations[reservation_id] = {
                "reserved": receipt["reserved"], "observed": 0, "sequence": 0,
                "attempt_id": receipt["attempt_id"], "policy_sha256": receipt["policy_sha256"],
            }
            expected_remaining = run["cap"] - run["committed"] - sum(item["reserved"] for item in reservations.values())
        else:
            current = reservations.get(reservation_id)
            if current is None:
                errors.append("receipt_reservation_missing")
                continue
            if receipt["attempt_id"] != current["attempt_id"] or receipt["policy_sha256"] != current["policy_sha256"]:
                errors.append("receipt_reservation_identity_mismatch")
                continue
            if receipt["reserved"] != current["reserved"]:
                errors.append("receipt_reserved_invalid")
                continue
            if phase == "mid_run":
                if receipt["sample_sequence"] != current["sequence"] + 1 or not current["observed"] <= receipt["observed"] <= current["reserved"]:
                    errors.append("receipt_phase_invalid")
                    continue
                current["observed"] = receipt["observed"]
                current["sequence"] = receipt["sample_sequence"]
                expected_remaining = run["cap"] - run["committed"] - sum(item["reserved"] for item in reservations.values())
            elif phase == "completion":
                if receipt["sample_sequence"] != current["sequence"] + 1 or not current["observed"] <= receipt["observed"] <= current["reserved"]:
                    errors.append("receipt_phase_invalid")
                    continue
                run["committed"] += receipt["observed"]
                del reservations[reservation_id]
                expected_remaining = run["cap"] - run["committed"] - sum(item["reserved"] for item in reservations.values())
            elif phase == "rollback":
                if receipt["sample_sequence"] != current["sequence"] or receipt["observed"] != current["observed"]:
                    errors.append("receipt_phase_invalid")
                    continue
                del reservations[reservation_id]
                expected_remaining = run["cap"] - run["committed"] - sum(item["reserved"] for item in reservations.values())
            else:
                errors.append("receipt_phase_invalid")
                continue
        if expected_remaining != receipt["remaining"] or expected_remaining < 0:
            errors.append("receipt_remaining_invalid")
    return tuple(dict.fromkeys(errors))


def project(receipts: Iterable[Mapping[str, Any]], *, cap: int, run_id: str) -> WorkUnitProjection:
    """Fold a verified receipt stream; invalid or unknown evidence is unsafe."""
    stream = [dict(receipt) for receipt in receipts if isinstance(receipt, Mapping) and receipt.get("run_id") == run_id]
    errors = validate_receipts(stream)
    if not _is_count(cap):
        raise ValueError("cap must be a non-negative integer")
    committed = 0
    live: dict[str, int] = {}
    last_sequence = 0
    last_receipt: dict[str, Any] | None = None
    safe = not errors
    for receipt in stream:
        if receipt.get("cap") != cap or receipt.get("source_state") in {"unknown", "late"}:
            safe = False
        reservation_id = str(receipt.get("reservation_id") or "")
        phase = receipt.get("phase")
        reserved = int(receipt.get("reserved") or 0)
        observed = int(receipt.get("observed") or 0)
        sample_sequence = int(receipt.get("sample_sequence") or 0)
        last_sequence = max(last_sequence, sample_sequence)
        if phase == "pre_dispatch":
            live[reservation_id] = reserved
        elif phase == "mid_run":
            pass
        elif phase == "completion":
            live.pop(reservation_id, None)
            committed += observed
        elif phase == "rollback":
            live.pop(reservation_id, None)
        last_receipt = receipt
    live_reservations = sum(live.values())
    remaining = cap - committed - live_reservations
    return WorkUnitProjection(committed, live_reservations, remaining, safe and remaining >= 0, last_sequence, last_receipt)


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
        invariant_fields = {
            "reserved": requested,
            "policy_sha256": policy_sha256,
            "cap": cap,
        }
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
