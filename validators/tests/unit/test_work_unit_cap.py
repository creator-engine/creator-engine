"""Focused CE603 work-unit-cap policy tests (pure and deterministic)."""
from __future__ import annotations

from pathlib import Path

import pytest

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
        attempt_id="attempt-1",
        reservation_id="reservation-1",
        requested=60,
        policy_sha256=POLICY_SHA,
        recorded_at=NOW,
    )
    assert retry.allowed
    assert retry.receipt == first.receipt


def test_retry_reuse_requires_the_extant_reservation_invariants():
    first = reserve(requested=60)
    matching = cap.reserve(
        (first.receipt,), cap=100, run_id="run-1", attempt_id="attempt-1",
        reservation_id="reservation-1", requested=60, policy_sha256=POLICY_SHA, recorded_at=NOW,
    )
    wrong_attempt = cap.reserve(
        (first.receipt,), cap=100, run_id="run-1", attempt_id="attempt/2",
        reservation_id="reservation-1", requested=60, policy_sha256=POLICY_SHA, recorded_at=NOW,
    )
    wrong_requested = cap.reserve(
        (first.receipt,), cap=100, run_id="run-1", attempt_id="attempt-1",
        reservation_id="reservation-1", requested=50, policy_sha256=POLICY_SHA, recorded_at=NOW,
    )
    terminal = cap.complete(
        (first.receipt,), cap=100, run_id="run-1", attempt_id="attempt-1",
        reservation_id="reservation-1", observed=1, policy_sha256=POLICY_SHA, recorded_at=NOW,
    )
    after_terminal = cap.reserve(
        (first.receipt, terminal.receipt), cap=100, run_id="run-1", attempt_id="attempt-1",
        reservation_id="reservation-1", requested=60, policy_sha256=POLICY_SHA, recorded_at=NOW,
    )
    assert matching.allowed and matching.persist is False
    assert not wrong_attempt.allowed and wrong_attempt.reason == "work_unit_retry_invariant_invalid"
    assert not wrong_requested.allowed and wrong_requested.reason == "work_unit_retry_invariant_invalid"
    assert not after_terminal.allowed and after_terminal.reason == "work_unit_retry_reservation_terminal"


@pytest.mark.parametrize("requested", [False, 0, -1, 1.5])
def test_non_positive_or_non_integer_requests_are_refused_before_receipt_creation(requested):
    with pytest.raises(ValueError, match="positive integer"):
        reserve(requested=requested)


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


def test_receipt_identity_and_semantic_invariants_fail_closed():
    reservation = reserve(requested=10)
    invalid_id = dict(reservation.receipt, receipt_id="0" * 64)
    assert "receipt_id_invalid" in cap.validate_receipts((invalid_id,))
    impossible = dict(reservation.receipt, remaining=99)
    impossible["receipt_sha256"] = cap.receipt_sha256(impossible)
    assert "receipt_remaining_invalid" in cap.validate_receipts((impossible,))


def test_interleaved_reservations_track_independent_lifecycles_and_terminals():
    first = reserve(requested=40, reservation_id="one")
    second = reserve((first.receipt,), requested=30, reservation_id="two")
    first_sample = cap.reconcile(
        (first.receipt, second.receipt), cap=100, run_id="run-1", attempt_id="attempt-1",
        reservation_id="one", sample_sequence=1, observed=20, policy_sha256=POLICY_SHA, recorded_at=NOW,
    )
    completed = cap.complete(
        (first.receipt, second.receipt, first_sample.receipt), cap=100, run_id="run-1",
        attempt_id="attempt-1", reservation_id="one", observed=20, policy_sha256=POLICY_SHA, recorded_at=NOW,
    )
    rolled_back = cap.rollback(
        (first.receipt, second.receipt, first_sample.receipt, completed.receipt), cap=100, run_id="run-1",
        attempt_id="attempt-1", reservation_id="two", policy_sha256=POLICY_SHA, recorded_at=NOW,
    )
    projection = cap.project((first.receipt, second.receipt, first_sample.receipt, completed.receipt, rolled_back.receipt), cap=100, run_id="run-1")
    assert completed.allowed and rolled_back.allowed
    assert projection.committed == 20
    assert projection.live_reservations == 0
    assert projection.remaining == 80


def test_reconcile_rejects_decreasing_observed_but_accepts_exact_replay():
    reservation = reserve(requested=10)
    first = cap.reconcile((reservation.receipt,), cap=100, run_id="run-1", attempt_id="attempt-1", reservation_id="reservation-1", sample_sequence=1, observed=8, policy_sha256=POLICY_SHA, recorded_at=NOW)
    replay = cap.reconcile((reservation.receipt, first.receipt), cap=100, run_id="run-1", attempt_id="attempt-1", reservation_id="reservation-1", sample_sequence=1, observed=8, policy_sha256=POLICY_SHA, recorded_at=NOW)
    decreasing = cap.reconcile((reservation.receipt, first.receipt), cap=100, run_id="run-1", attempt_id="attempt-1", reservation_id="reservation-1", sample_sequence=2, observed=7, policy_sha256=POLICY_SHA, recorded_at=NOW)
    assert replay.allowed and replay.receipt == first.receipt
    assert not decreasing.allowed
    assert decreasing.reason == "work_unit_observed_decreased"
