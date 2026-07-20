"""Direct tests for neutral work-unit receipt primitives."""
from __future__ import annotations

from creator_engine_validator import work_unit_ledger as ledger
from creator_engine_validator.runner import work_unit_cap as cap


def test_neutral_ledger_receipt_round_trips_through_runner_projection():
    receipt = ledger.make_receipt(
        run_id="run-1", attempt_id="attempt-1", reservation_id="reservation-1",
        phase="pre_dispatch", cap=100, reserved=10, observed=0, remaining=90,
        sample_sequence=0, source_state="measured", policy_sha256="a" * 64,
        previous_receipt_sha256=ledger.GENESIS_RECEIPT_SHA256,
        recorded_at="2026-07-18T00:00:00Z",
    )
    assert ledger.validate_receipts((receipt,)) == ()
    assert cap.validate_receipts((receipt,)) == ()
    assert cap.project((receipt,), cap=100, run_id="run-1") == ledger.project(
        (receipt,), cap=100, run_id="run-1"
    )


def test_projection_refuses_a_malformed_entry_anywhere_in_the_receipt_stream():
    receipt = ledger.make_receipt(
        run_id="run-1", attempt_id="attempt-1", reservation_id="reservation-1",
        phase="pre_dispatch", cap=100, reserved=10, observed=0, remaining=90,
        sample_sequence=0, source_state="measured", policy_sha256="a" * 64,
        previous_receipt_sha256=ledger.GENESIS_RECEIPT_SHA256,
        recorded_at="2026-07-18T00:00:00Z",
    )

    projection = ledger.project((receipt, {"not": "a CE603 receipt"}), cap=100, run_id="run-1")

    assert not projection.safe
