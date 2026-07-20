"""Neutral CE603 receipt serialization, validation, and projection primitives.

This substrate deliberately imports neither runtime version line.  It contains
only deterministic receipt mechanics that can be used by both the v1 ledger
runtime and the v3 runner policy facade.
"""
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
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


@dataclass(frozen=True)
class WorkUnitProjection:
    committed: int
    live_reservations: int
    remaining: int
    safe: bool
    last_sequence: int
    last_receipt: dict[str, Any] | None


def canonical_json_text(value: Mapping[str, Any]) -> str:
    """Serialize a receipt deterministically using the ledger's JSON format."""
    return json.dumps(dict(value), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return canonical_json_text(value).encode("utf-8")


def receipt_sha256(receipt: Mapping[str, Any]) -> str:
    material = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def receipt_id(material: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def make_receipt(
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
    if not all(is_count(value) for value in values):
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
        "receipt_id": receipt_id(identity),
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
        if not all(isinstance(receipt.get(name), str) and IDENTIFIER_RE.fullmatch(receipt[name]) for name in strings):
            errors.append("receipt_identifier_invalid")
            continue
        if not isinstance(receipt.get("recorded_at"), str) or not receipt["recorded_at"]:
            errors.append("receipt_recorded_at_invalid")
            continue
        if not all(isinstance(receipt.get(name), str) and SHA256_RE.fullmatch(receipt[name]) for name in ("policy_sha256", "previous_receipt_sha256", "receipt_sha256", "receipt_id")):
            errors.append("receipt_hash_invalid")
            continue
        identity = {name: receipt[name] for name in ("run_id", "attempt_id", "reservation_id", "phase", "sample_sequence", "previous_receipt_sha256")}
        if receipt["receipt_id"] != receipt_id(identity):
            errors.append("receipt_id_invalid")
        if receipt.get("unit") != UNIT or receipt.get("unit_version") != UNIT_VERSION:
            errors.append("receipt_unit_invalid")
        if receipt.get("phase") not in PHASES or receipt.get("source_state") not in SOURCE_STATES:
            errors.append("receipt_vocabulary_invalid")
        if not all(is_count(receipt.get(name)) for name in ("cap", "reserved", "observed", "remaining", "sample_sequence")):
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
        reservation_id_value = receipt["reservation_id"]
        phase = receipt["phase"]
        expected_remaining: int | None = None
        if phase == "pre_dispatch":
            if reservation_id_value in reservations or receipt["sample_sequence"] != 0 or receipt["observed"] != 0 or receipt["reserved"] <= 0:
                errors.append("receipt_phase_invalid")
                continue
            reservations[reservation_id_value] = {
                "reserved": receipt["reserved"], "observed": 0, "sequence": 0,
                "attempt_id": receipt["attempt_id"], "policy_sha256": receipt["policy_sha256"],
            }
            expected_remaining = run["cap"] - run["committed"] - sum(item["reserved"] for item in reservations.values())
        else:
            current = reservations.get(reservation_id_value)
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
                del reservations[reservation_id_value]
                expected_remaining = run["cap"] - run["committed"] - sum(item["reserved"] for item in reservations.values())
            elif phase == "rollback":
                if receipt["sample_sequence"] != current["sequence"] or receipt["observed"] != current["observed"]:
                    errors.append("receipt_phase_invalid")
                    continue
                del reservations[reservation_id_value]
                expected_remaining = run["cap"] - run["committed"] - sum(item["reserved"] for item in reservations.values())
            else:
                errors.append("receipt_phase_invalid")
                continue
        if expected_remaining != receipt["remaining"] or expected_remaining < 0:
            errors.append("receipt_remaining_invalid")
    return tuple(dict.fromkeys(errors))


def project(receipts: Iterable[Mapping[str, Any]], *, cap: int, run_id: str) -> WorkUnitProjection:
    """Fold a verified receipt stream; invalid or unknown evidence is unsafe."""
    receipt_stream = tuple(receipts)
    errors = validate_receipts(receipt_stream)
    stream = [dict(receipt) for receipt in receipt_stream if isinstance(receipt, Mapping) and receipt.get("run_id") == run_id]
    if not is_count(cap):
        raise ValueError("cap must be a non-negative integer")
    committed = 0
    live: dict[str, int] = {}
    last_sequence = 0
    last_receipt: dict[str, Any] | None = None
    safe = not errors
    for receipt in stream:
        if receipt.get("cap") != cap or receipt.get("source_state") in {"unknown", "late"}:
            safe = False
        reservation_id_value = str(receipt.get("reservation_id") or "")
        phase = receipt.get("phase")
        reserved = int(receipt.get("reserved") or 0)
        observed = int(receipt.get("observed") or 0)
        sample_sequence = int(receipt.get("sample_sequence") or 0)
        last_sequence = max(last_sequence, sample_sequence)
        if phase == "pre_dispatch":
            live[reservation_id_value] = reserved
        elif phase == "completion":
            live.pop(reservation_id_value, None)
            committed += observed
        elif phase == "rollback":
            live.pop(reservation_id_value, None)
        last_receipt = receipt
    live_reservations = sum(live.values())
    remaining = cap - committed - live_reservations
    return WorkUnitProjection(committed, live_reservations, remaining, safe and remaining >= 0, last_sequence, last_receipt)
