"""Unit tests for the Side-Effect Ledger runtime (RV1-040/041/042).

Drives ``creator_engine_validator.side_effect_ledger_runtime`` directly. The
runtime appends redaction-safe deterministic JSON records under a hash chain
and verifies/replays them. No tmux, GitHub, network, container, or provider
surface is touched; records are stdlib-``json`` bytes per the Option B format
split.
"""
from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import side_effect_ledger_runtime as runtime
from creator_engine_validator.runner import work_unit_cap as cap


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


CONTROLLER = "hermes-primary"
LANE = "pco-slice4-impl"
NOW = datetime(2026, 5, 25, 12, 11, 0, tzinfo=UTC)


def _claim(awl_root: Path, controller: str = CONTROLLER, lane: str = LANE, *, released: bool = False) -> Path:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller,
        "lane_id": lane,
        "record_timestamp": f"source-controlled:claims/{controller}/{lane}.yaml",
        "worktree_path": "/worktrees/pco-slice4-impl",
        "envelope_ref": ".hermes/envelopes/pco-slice4.md",
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{controller}/{lane}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{controller}/{lane}.yaml",
    }
    if released:
        record["released_at"] = "2026-05-25T04:05:00Z"
        record["release_reason"] = "completed"
    path = awl_root / "claims" / controller / f"{lane}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _kwargs(tmp_path: Path, **overrides):
    sel_root = tmp_path / "side-effect-ledger"
    awl_root = tmp_path / ".hermes" / "active-work-ledger"
    base = dict(
        controller_id=CONTROLLER,
        lane_id=LANE,
        claim_ref=f"claims/{CONTROLLER}/{LANE}.yaml",
        effect_id="effect-tracked-file-change-001",
        effect_kind="tracked_file_change",
        effect_status="succeeded",
        summary="Created a schema file.",
        occurred_at="2026-05-25T12:10:00Z",
        repo_root=str(tmp_path),
        side_effect_ledger_root=str(sel_root),
        active_work_ledger_root=str(awl_root),
        now=NOW,
    )
    base.update(overrides)
    return base


def _append(tmp_path: Path, **overrides):
    return runtime.record(**_kwargs(tmp_path, **overrides))


def _work_unit_receipt():
    return cap.reserve(
        (), cap=100, run_id="run", attempt_id="attempt", reservation_id="reservation",
        requested=10, policy_sha256="a" * 64, recorded_at="2026-07-18T00:00:00Z",
    ).receipt


def _successor_receipt(receipt):
    return cap.reserve(
        (receipt,), cap=100, run_id="run", attempt_id="attempt", reservation_id="reservation-2",
        requested=10, policy_sha256="a" * 64, recorded_at="2026-07-18T00:01:00Z",
    ).receipt


# ---------------------------------------------------------------------------
# Append + hash chain
# ---------------------------------------------------------------------------


def test_first_record_is_genesis_with_zero_previous_sha(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    result = _append(tmp_path)
    assert result.sequence == 1
    assert result.previous_record_sha256 == runtime.GENESIS_SHA
    assert result.record_path.is_file()
    # record file bytes hash to the reported record sha256
    assert hashlib.sha256(result.record_path.read_bytes()).hexdigest() == result.record_sha256
    # head manifest exists and points at the genesis record
    assert result.head_path.is_file()
    head = json.loads(result.head_path.read_text(encoding="utf-8"))
    assert head["sequence"] == 1
    assert head["head_sha256"] == result.record_sha256


def test_records_are_grouped_by_controller_lane_utc_day(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    result = _append(tmp_path)
    rel = result.record_path.relative_to(tmp_path / "side-effect-ledger")
    assert rel.parts[0] == CONTROLLER
    assert rel.parts[1] == LANE
    assert rel.parts[2] == "2026-05-25"
    assert rel.name == "000001-effect-tracked-file-change-001.json"


def test_second_record_chains_to_previous_record_sha(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first = _append(tmp_path, effect_id="effect-a")
    second = _append(tmp_path, effect_id="effect-b")
    assert second.sequence == 2
    assert second.previous_record_sha256 == first.record_sha256
    head = json.loads(second.head_path.read_text(encoding="utf-8"))
    assert head["sequence"] == 2
    assert head["head_sha256"] == second.record_sha256


def test_first_sealed_record_has_explicit_genesis_seal(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    result = _append(tmp_path)

    assert result.record["details"]["prev_seal_sha256"] == runtime.GENESIS_SHA


def test_verify_passes_for_a_valid_explicit_seal_chain(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first = _append(tmp_path, effect_id="effect-sealed-a")
    second = _append(tmp_path, effect_id="effect-sealed-b")

    result = runtime.verify(side_effect_ledger_root=tmp_path / "side-effect-ledger")

    assert result.ok, result.errors
    assert second.record["details"]["prev_seal_sha256"] == first.record_sha256


def test_verify_refuses_altered_middle_explicit_seal(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    _append(tmp_path, effect_id="effect-sealed-a")
    middle = _append(tmp_path, effect_id="effect-sealed-b")
    _append(tmp_path, effect_id="effect-sealed-c")
    record = json.loads(middle.record_path.read_text(encoding="utf-8"))
    record["details"]["prev_seal_sha256"] = runtime.GENESIS_SHA
    middle.record_path.write_text(runtime._canonical_bytes(record), encoding="utf-8")

    result = runtime.verify(side_effect_ledger_root=tmp_path / "side-effect-ledger")

    assert not result.ok
    assert any("seal-chain link broken" in error for error in result.errors)


def test_verify_refuses_deleted_explicit_seal_record(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    _append(tmp_path, effect_id="effect-sealed-a")
    middle = _append(tmp_path, effect_id="effect-sealed-b")
    _append(tmp_path, effect_id="effect-sealed-c")
    middle.record_path.unlink()

    result = runtime.verify(side_effect_ledger_root=tmp_path / "side-effect-ledger")

    assert not result.ok
    assert any("seal-chain link broken" in error for error in result.errors)


def test_verify_refuses_reordered_explicit_seal_records(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first = _append(tmp_path, effect_id="effect-sealed-a")
    second = _append(tmp_path, effect_id="effect-sealed-b")
    first_record = json.loads(first.record_path.read_text(encoding="utf-8"))
    second_record = json.loads(second.record_path.read_text(encoding="utf-8"))
    first_record["sequence"], second_record["sequence"] = second_record["sequence"], first_record["sequence"]
    first.record_path.write_text(runtime._canonical_bytes(first_record), encoding="utf-8")
    second.record_path.write_text(runtime._canonical_bytes(second_record), encoding="utf-8")

    result = runtime.verify(side_effect_ledger_root=tmp_path / "side-effect-ledger")

    assert not result.ok
    assert any("seal-chain link broken" in error for error in result.errors)


def test_legacy_prev_seal_detail_is_ignored_and_first_new_seal_is_genesis(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    legacy = _append(tmp_path, effect_id="effect-legacy")
    legacy_record = json.loads(legacy.record_path.read_text(encoding="utf-8"))
    legacy_record["details"]["prev_seal_sha256"] = "legacy-note"
    del legacy_record["details"][runtime.SEAL_SCHEME]
    legacy.record_path.write_text(runtime._canonical_bytes(legacy_record), encoding="utf-8")
    head = json.loads(legacy.head_path.read_text(encoding="utf-8"))
    head["head_sha256"] = hashlib.sha256(legacy.record_path.read_bytes()).hexdigest()
    legacy.head_path.write_text(json.dumps(head, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    assert runtime.verify(side_effect_ledger_root=tmp_path / "side-effect-ledger").ok
    sealed = _append(tmp_path, effect_id="effect-first-sealed")

    assert sealed.record["details"][runtime.PREV_SEAL_SHA256] == runtime.GENESIS_SHA
    assert sealed.record["details"][runtime.SEAL_SCHEME] == runtime.SEAL_SCHEME_VALUE


def test_verify_refuses_missing_prev_seal_after_sealed_record(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    _append(tmp_path, effect_id="effect-sealed-a")
    sealed = _append(tmp_path, effect_id="effect-sealed-b")
    record = json.loads(sealed.record_path.read_text(encoding="utf-8"))
    assert record["details"][runtime.SEAL_SCHEME] == runtime.SEAL_SCHEME_VALUE
    del record["details"][runtime.PREV_SEAL_SHA256]
    sealed.record_path.write_text(runtime._canonical_bytes(record), encoding="utf-8")

    result = runtime.verify(side_effect_ledger_root=tmp_path / "side-effect-ledger")

    assert not result.ok
    assert any("seal-chain link broken" in error for error in result.errors)


def test_verify_refuses_missing_seal_marker_after_sealed_predecessor(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    _append(tmp_path, effect_id="effect-sealed-a")
    sealed = _append(tmp_path, effect_id="effect-sealed-b")
    record = json.loads(sealed.record_path.read_text(encoding="utf-8"))
    del record["details"][runtime.SEAL_SCHEME]
    sealed.record_path.write_text(runtime._canonical_bytes(record), encoding="utf-8")

    result = runtime.verify(side_effect_ledger_root=tmp_path / "side-effect-ledger")

    assert not result.ok
    assert any("seal-chain gap" in error for error in result.errors)


def test_writer_overwrites_attacker_controlled_prev_seal_detail(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)

    result = _append(
        tmp_path,
        details={
            runtime.PREV_SEAL_SHA256: "attacker-controlled",
            runtime.SEAL_SCHEME: "attacker-controlled",
        },
    )

    assert result.record["details"][runtime.PREV_SEAL_SHA256] == runtime.GENESIS_SHA
    assert result.record["details"][runtime.SEAL_SCHEME] == runtime.SEAL_SCHEME_VALUE


def test_work_unit_reservation_uses_the_single_record_writer(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    receipt = _work_unit_receipt()
    result = runtime.record_work_unit_reservation(receipt=receipt, **_kwargs(tmp_path))
    fragments = [result.record["details"][key] for key in sorted(result.record["details"]) if key.startswith("work_unit_receipt_part_")]
    assert json.loads(bytes.fromhex("".join(fragments)).decode("utf-8")) == receipt
    assert result.record["effect_id"].startswith("work-unit-reservation-")
    assert runtime._durable_work_unit_receipts(tmp_path / "side-effect-ledger", CONTROLLER, LANE) == (receipt,)


def test_work_unit_reservation_persists_a_valid_durable_successor_under_lane_lock(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first_receipt = _work_unit_receipt()
    first = runtime.record_work_unit_reservation(receipt=first_receipt, **_kwargs(tmp_path))
    second_receipt = _successor_receipt(first_receipt)
    second = runtime.record_work_unit_reservation(receipt=second_receipt, **_kwargs(tmp_path))

    assert second_receipt["previous_receipt_sha256"] == first_receipt["receipt_sha256"]
    assert (first.sequence, second.sequence) == (1, 2)
    assert runtime._durable_work_unit_receipts(tmp_path / "side-effect-ledger", CONTROLLER, LANE) == (
        first_receipt,
        second_receipt,
    )


def test_corrupt_durable_ce603_history_refuses_successor_without_ledger_write(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first_receipt = _work_unit_receipt()
    first = runtime.record_work_unit_reservation(receipt=first_receipt, **_kwargs(tmp_path))
    record = json.loads(first.record_path.read_text(encoding="utf-8"))
    record["details"] = {"work_unit_receipt_part_000": "zz"}
    first.record_path.write_text(runtime._canonical_bytes(record), encoding="utf-8")
    head = json.loads(first.head_path.read_text(encoding="utf-8"))
    head["head_sha256"] = hashlib.sha256(first.record_path.read_bytes()).hexdigest()
    first.head_path.write_text(json.dumps(head, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    before = {
        path.relative_to(tmp_path / "side-effect-ledger").as_posix(): path.read_bytes()
        for path in (tmp_path / "side-effect-ledger").rglob("*.json")
    }

    with pytest.raises(runtime.WorkUnitReceiptHistoryError):
        runtime.record_work_unit_reservation(receipt=_successor_receipt(first_receipt), **_kwargs(tmp_path))

    after = {
        path.relative_to(tmp_path / "side-effect-ledger").as_posix(): path.read_bytes()
        for path in (tmp_path / "side-effect-ledger").rglob("*.json")
    }
    assert after == before


def test_head_without_records_refuses_successor_without_ledger_mutation(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first_receipt = _work_unit_receipt()
    first = runtime.record_work_unit_reservation(receipt=first_receipt, **_kwargs(tmp_path))
    lane_root = tmp_path / "side-effect-ledger" / CONTROLLER / LANE
    before = {
        path.relative_to(lane_root).as_posix(): path.read_bytes()
        for path in lane_root.rglob("*.json")
    }
    first.record_path.unlink()

    with pytest.raises(runtime.WorkUnitReceiptHistoryError):
        runtime.record_work_unit_reservation(receipt=_successor_receipt(first_receipt), **_kwargs(tmp_path))

    after = {
        path.relative_to(lane_root).as_posix(): path.read_bytes()
        for path in lane_root.rglob("*.json")
    }
    assert after == {runtime.HEAD_FILENAME: before[runtime.HEAD_FILENAME]}


def test_populated_headless_lane_refuses_without_writing_record_or_head(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first = _append(tmp_path, effect_id="effect-a")
    first.head_path.unlink()
    lane_root = tmp_path / "side-effect-ledger" / CONTROLLER / LANE
    before = {
        path.relative_to(lane_root).as_posix(): path.read_bytes()
        for path in lane_root.rglob("*.json")
    }

    with pytest.raises(runtime.LedgerRecordError):
        _append(tmp_path, effect_id="effect-b")

    after = {
        path.relative_to(lane_root).as_posix(): path.read_bytes()
        for path in lane_root.rglob("*.json")
    }
    assert after == before


@pytest.mark.parametrize("head_bytes", (b"not json\n", b"[\"not an object\"]\n"))
def test_unreadable_or_malformed_head_refuses_before_reservation_mutation(
    tmp_path: Path, head_bytes: bytes
):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first_receipt = _work_unit_receipt()
    first = runtime.record_work_unit_reservation(receipt=first_receipt, **_kwargs(tmp_path))
    first.head_path.write_bytes(head_bytes)
    lane_root = tmp_path / "side-effect-ledger" / CONTROLLER / LANE
    before = {
        path.relative_to(lane_root).as_posix(): path.read_bytes()
        for path in lane_root.rglob("*.json")
    }

    with pytest.raises(runtime.LedgerRecordError):
        runtime.record_work_unit_reservation(receipt=_successor_receipt(first_receipt), **_kwargs(tmp_path))

    after = {
        path.relative_to(lane_root).as_posix(): path.read_bytes()
        for path in lane_root.rglob("*.json")
    }
    assert after == before


def test_generic_record_and_reservation_share_one_lane_lock(tmp_path: Path, monkeypatch):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    generic_record_written = threading.Event()
    release_generic_record = threading.Event()
    original_atomic_write = runtime._atomic_write

    def barrier_atomic_write(path: Path, content: str) -> None:
        if path.name == "000001-effect-generic.json":
            generic_record_written.set()
            assert release_generic_record.wait(timeout=5)
        original_atomic_write(path, content)

    monkeypatch.setattr(runtime, "_atomic_write", barrier_atomic_write)
    with ThreadPoolExecutor(max_workers=2) as pool:
        generic = pool.submit(_append, tmp_path, effect_id="effect-generic")
        assert generic_record_written.wait(timeout=5)
        reservation = pool.submit(
            runtime.record_work_unit_reservation,
            receipt=_work_unit_receipt(), **_kwargs(tmp_path),
        )
        assert not reservation.done()
        release_generic_record.set()
        generic_result = generic.result(timeout=5)
        reservation_result = reservation.result(timeout=5)
    assert generic_result.sequence == 1
    assert reservation_result.sequence == 2
    verified = runtime.verify(
        side_effect_ledger_root=str(tmp_path / "side-effect-ledger"), active_work_ledger_root=str(awl),
    )
    assert verified.ok, verified.errors
    assert verified.summary["chains"][0]["record_count"] == 2


def test_ce603_shaped_record_without_fragments_refuses_before_reservation_mutation(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    runtime.record_work_unit_reservation(receipt=_work_unit_receipt(), **_kwargs(tmp_path))
    record_path = next((tmp_path / "side-effect-ledger").rglob("*-work-unit-reservation-*.json"))
    record = json.loads(record_path.read_text(encoding="utf-8"))
    del record["details"]
    record_path.write_text(runtime._canonical_bytes(record), encoding="utf-8")
    head_path = tmp_path / "side-effect-ledger" / CONTROLLER / LANE / runtime.HEAD_FILENAME
    head = json.loads(head_path.read_text(encoding="utf-8"))
    head["head_sha256"] = hashlib.sha256(record_path.read_bytes()).hexdigest()
    head_path.write_text(json.dumps(head, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(runtime.WorkUnitReceiptHistoryError):
        runtime._durable_work_unit_receipts(tmp_path / "side-effect-ledger", CONTROLLER, LANE)


@pytest.mark.parametrize("fragment", ("zz", "7b", "7b7d"))
def test_corrupt_persisted_ce603_receipt_history_refuses_before_mutation(tmp_path: Path, fragment: str):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    runtime.record_work_unit_reservation(receipt=_work_unit_receipt(), **_kwargs(tmp_path))
    record_path = next((tmp_path / "side-effect-ledger").rglob("*-work-unit-reservation-*.json"))
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["details"] = {"work_unit_receipt_part_000": fragment}
    record_path.write_text(runtime._canonical_bytes(record), encoding="utf-8")
    head_path = tmp_path / "side-effect-ledger" / CONTROLLER / LANE / runtime.HEAD_FILENAME
    head = json.loads(head_path.read_text(encoding="utf-8"))
    head["head_sha256"] = hashlib.sha256(record_path.read_bytes()).hexdigest()
    head_path.write_text(json.dumps(head, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    assert runtime.verify(
        side_effect_ledger_root=tmp_path / "side-effect-ledger", active_work_ledger_root=awl,
    ).ok
    with pytest.raises(runtime.WorkUnitReceiptHistoryError):
        runtime._durable_work_unit_receipts(tmp_path / "side-effect-ledger", CONTROLLER, LANE)


def test_record_is_valid_under_existing_side_effect_ledger_substrate(tmp_path: Path):
    from creator_engine_validator.checks.side_effect_ledger import (
        validate_side_effect_ledger_record,
    )

    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    result = _append(tmp_path)
    errors = validate_side_effect_ledger_record(result.record, result.record_path)
    assert [error.code for error in errors] == ["PCO-059"]
    assert errors[0].path.endswith("details.prev_seal_sha256")


# ---------------------------------------------------------------------------
# Refusals — leave no partial record/head mutation
# ---------------------------------------------------------------------------


def test_collision_with_existing_record_is_refused(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first = _append(tmp_path, effect_id="effect-a")
    # Pre-create the file the next sequence would write to.
    sel_root = tmp_path / "side-effect-ledger"
    collision = sel_root / CONTROLLER / LANE / "2026-05-25" / "000002-effect-b.json"
    collision.write_text("PRE-EXISTING\n", encoding="utf-8")
    with pytest.raises(runtime.RecordCollision):
        _append(tmp_path, effect_id="effect-b")
    assert collision.read_text(encoding="utf-8") == "PRE-EXISTING\n"
    # head still at the first sequence — no mutation on refusal
    head = json.loads(first.head_path.read_text(encoding="utf-8"))
    assert head["sequence"] == 1


def test_secret_in_details_is_refused_and_writes_nothing(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    with pytest.raises(runtime.SecretMaterialRefused):
        _append(tmp_path, details={"api_token": "sk-abcdef1234567890"})
    sel_root = tmp_path / "side-effect-ledger"
    assert list(sel_root.rglob("*.json")) == []


def test_secret_in_evidence_ref_is_refused_and_writes_nothing(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    with pytest.raises(runtime.SecretMaterialRefused):
        _append(tmp_path, evidence_refs=["-----BEGIN RSA PRIVATE KEY-----"])
    sel_root = tmp_path / "side-effect-ledger"
    assert list(sel_root.rglob("*.json")) == []


def test_details_must_be_a_json_object(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    with pytest.raises(runtime.DetailsNotObject):
        _append(tmp_path, details=["not", "an", "object"])


def test_missing_claim_is_refused(tmp_path: Path):
    # no claim written
    with pytest.raises(runtime.ClaimBindingError):
        _append(tmp_path)
    sel_root = tmp_path / "side-effect-ledger"
    assert list(sel_root.rglob("*.json")) == []


def test_released_claim_is_refused(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl, released=True)
    with pytest.raises(runtime.ClaimBindingError):
        _append(tmp_path)


def test_claim_controller_lane_mismatch_is_refused(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    # claim names a different lane than the record claims to bind
    _claim(awl, lane="some-other-lane")
    with pytest.raises(runtime.ClaimBindingError):
        _append(tmp_path, claim_ref=f"claims/{CONTROLLER}/some-other-lane.yaml")


# ---------------------------------------------------------------------------
# Verify + deterministic replay
# ---------------------------------------------------------------------------


def test_verify_passes_for_a_valid_chain(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first = _append(tmp_path, effect_id="effect-a", effect_kind="tracked_file_change")
    last = _append(tmp_path, effect_id="effect-b", effect_kind="git_mutation")
    # Model an existing valid unsealed lane.  Its original byte-chain and head
    # remain valid, but its records predate explicit seals.
    first_record = json.loads(first.record_path.read_text(encoding="utf-8"))
    last_record = json.loads(last.record_path.read_text(encoding="utf-8"))
    del first_record["details"]["prev_seal_sha256"]
    del last_record["details"]["prev_seal_sha256"]
    del first_record["details"][runtime.SEAL_SCHEME]
    del last_record["details"][runtime.SEAL_SCHEME]
    first.record_path.write_text(runtime._canonical_bytes(first_record), encoding="utf-8")
    last_record["previous_record_sha256"] = hashlib.sha256(first.record_path.read_bytes()).hexdigest()
    last.record_path.write_text(runtime._canonical_bytes(last_record), encoding="utf-8")
    head = json.loads(last.head_path.read_text(encoding="utf-8"))
    head["head_sha256"] = hashlib.sha256(last.record_path.read_bytes()).hexdigest()
    last.head_path.write_text(json.dumps(head, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    result = runtime.verify(
        side_effect_ledger_root=str(tmp_path / "side-effect-ledger"),
        active_work_ledger_root=str(awl),
    )
    assert result.ok, result.errors
    assert result.summary["record_count"] == 2
    assert result.summary["effect_kind_counts"]["tracked_file_change"] == 1
    assert result.summary["effect_kind_counts"]["git_mutation"] == 1
    chain = result.summary["chains"][0]
    assert chain["head_sha256"] == head["head_sha256"]
    assert chain["last_record_ref"].endswith("000002-effect-b.json")

    sealed = _append(tmp_path, effect_id="effect-c")
    assert sealed.record["details"]["prev_seal_sha256"] == runtime.GENESIS_SHA
    assert runtime.verify(side_effect_ledger_root=tmp_path / "side-effect-ledger").ok


def test_verify_detects_a_tampered_earlier_record(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    first = _append(tmp_path, effect_id="effect-a")
    _append(tmp_path, effect_id="effect-b")
    # tamper: mutate the earlier record's bytes while keeping it schema-valid
    record = json.loads(first.record_path.read_text(encoding="utf-8"))
    record["summary"] = "Tampered summary."
    first.record_path.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    result = runtime.verify(side_effect_ledger_root=str(tmp_path / "side-effect-ledger"))
    assert not result.ok
    assert result.errors


def test_verify_detects_a_deleted_intermediate_record(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    _append(tmp_path, effect_id="effect-a")
    middle = _append(tmp_path, effect_id="effect-b")
    _append(tmp_path, effect_id="effect-c")
    middle.record_path.unlink()
    result = runtime.verify(side_effect_ledger_root=str(tmp_path / "side-effect-ledger"))
    assert not result.ok
    assert result.errors


def test_verify_detects_head_mismatch(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    last = _append(tmp_path)
    head = json.loads(last.head_path.read_text(encoding="utf-8"))
    head["head_sha256"] = "0" * 64
    last.head_path.write_text(json.dumps(head, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    result = runtime.verify(side_effect_ledger_root=str(tmp_path / "side-effect-ledger"))
    assert not result.ok


def test_verify_detects_unbound_claim_when_ledger_root_provided(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    _append(tmp_path)
    # verify against an empty active-work-ledger root: claim no longer resolves
    empty_awl = tmp_path / "empty-awl"
    empty_awl.mkdir()
    result = runtime.verify(
        side_effect_ledger_root=str(tmp_path / "side-effect-ledger"),
        active_work_ledger_root=str(empty_awl),
    )
    assert not result.ok


def test_verify_replay_summary_is_deterministic(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    _append(tmp_path, effect_id="effect-a")
    _append(tmp_path, effect_id="effect-b")
    sel = str(tmp_path / "side-effect-ledger")
    first = runtime.verify(side_effect_ledger_root=sel)
    second = runtime.verify(side_effect_ledger_root=sel)
    assert json.dumps(first.summary, sort_keys=True) == json.dumps(second.summary, sort_keys=True)
