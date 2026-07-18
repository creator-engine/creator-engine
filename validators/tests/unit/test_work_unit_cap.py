"""Focused CE603 work-unit-cap policy tests (pure and deterministic)."""
from __future__ import annotations

from pathlib import Path

from creator_engine_validator.runner import work_unit_cap as cap
from creator_engine_validator.schema import validate_with_schema


POLICY_SHA = "a" * 64
NOW = "2026-07-18T00:00:00Z"


def reserve(receipts=(), *, requested=10, reservation_id="reservation-1"):
    return cap.reserve(
        receipts,
        cap=100,
        run_id="run-1",
        attempt_id="attempt-1",
        reservation_id=reservation_id,
        requested=requested,
        policy_sha256=POLICY_SHA,
        recorded_at=NOW,
    )


def test_reservation_at_exact_cap_is_allowed_and_over_cap_is_denied():
    exact = reserve(requested=100)
    assert exact.allowed
    assert exact.receipt["unit"] == "ce.raw_tokens.v1"
    assert exact.receipt["remaining"] == 0

    denied = reserve(requested=101)
    assert not denied.allowed
    assert denied.reason == "work_unit_cap_exhausted"


def test_two_competing_reservations_use_the_projection_not_a_second_envelope():
    first = reserve(requested=60)
    second = reserve((first.receipt,), requested=50, reservation_id="reservation-2")
    assert first.allowed
    assert not second.allowed


def test_retry_reuses_a_live_reservation_without_reserving_again():
    first = reserve(requested=60)
    retry = cap.reserve(
        (first.receipt,),
        cap=100,
        run_id="run-1",
        attempt_id="attempt-2",
        reservation_id="reservation-1",
        requested=60,
        policy_sha256=POLICY_SHA,
        recorded_at=NOW,
    )
    assert retry.allowed
    assert retry.receipt == first.receipt


def test_reconcile_is_idempotent_and_a_gap_fails_closed():
    reservation = reserve()
    sample = cap.reconcile(
        (reservation.receipt,),
        cap=100,
        run_id="run-1",
        attempt_id="attempt-1",
        reservation_id="reservation-1",
        sample_sequence=1,
        observed=8,
        policy_sha256=POLICY_SHA,
        recorded_at=NOW,
    )
    duplicate = cap.reconcile(
        (reservation.receipt, sample.receipt),
        cap=100,
        run_id="run-1",
        attempt_id="attempt-1",
        reservation_id="reservation-1",
        sample_sequence=1,
        observed=8,
        policy_sha256=POLICY_SHA,
        recorded_at=NOW,
    )
    gap = cap.reconcile(
        (reservation.receipt, sample.receipt),
        cap=100,
        run_id="run-1",
        attempt_id="attempt-1",
        reservation_id="reservation-1",
        sample_sequence=3,
        observed=12,
        policy_sha256=POLICY_SHA,
        recorded_at=NOW,
    )
    assert sample.allowed
    assert duplicate.receipt == sample.receipt
    assert not gap.allowed
    assert gap.receipt["source_state"] == "unknown"


def test_receipt_digests_are_canonical_and_tampering_is_rejected():
    reservation = reserve()
    sample = cap.reconcile(
        (reservation.receipt,),
        cap=100,
        run_id="run-1",
        attempt_id="attempt-1",
        reservation_id="reservation-1",
        sample_sequence=1,
        observed=8,
        policy_sha256=POLICY_SHA,
        recorded_at=NOW,
    )
    assert sample.receipt["previous_receipt_sha256"] == reservation.receipt["receipt_sha256"]
    tampered = dict(sample.receipt, observed=9)
    assert cap.validate_receipts((reservation.receipt, tampered)) == ("receipt_digest_invalid",)


def test_closed_receipt_schema_accepts_only_the_ce603_contract():
    receipt = reserve().receipt
    schema = Path(__file__).parents[2] / "creator_engine_validator" / "schemas" / "work-unit-cap.schema.yaml"
    assert validate_with_schema(receipt, schema, "receipt", code="CE603", contract=schema) == []
    assert validate_with_schema(dict(receipt, extra=True), schema, "receipt", code="CE603", contract=schema)
