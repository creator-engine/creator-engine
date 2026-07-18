"""Unit tests for the Side-Effect Ledger runtime (RV1-040/041/042).

Drives ``creator_engine_validator.side_effect_ledger_runtime`` directly. The
runtime appends redaction-safe deterministic JSON records under a hash chain
and verifies/replays them. No tmux, GitHub, network, container, or provider
surface is touched; records are stdlib-``json`` bytes per the Option B format
split.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import side_effect_ledger_runtime as runtime


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


def test_work_unit_reservation_uses_the_single_record_writer(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    receipt = {"receipt_id": "r", "unit": "ce.raw_tokens.v1", "unit_version": 1}
    result = runtime.record_work_unit_reservation(receipt=receipt, **_kwargs(tmp_path))
    fragments = [result.record["details"][key] for key in sorted(result.record["details"]) if key.startswith("work_unit_receipt_part_")]
    assert json.loads(bytes.fromhex("".join(fragments)).decode("utf-8")) == receipt
    assert result.record["effect_id"].startswith("work-unit-reservation-")
    assert not runtime.work_unit_reservation_evidence(
        receipt,
        side_effect_ledger_root=tmp_path / "side-effect-ledger", active_work_ledger_root=awl,
        controller_id=CONTROLLER, lane_id=LANE, run_id="run", attempt_id="attempt",
        reservation_id="reservation", policy_sha256="a" * 64,
    )["valid"]


def test_durable_work_unit_reservation_reuses_after_crash_and_never_overbooks(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    def reserve_once(reservation_id: str):
        return runtime.reserve_work_unit_reservation(
            cap=100, run_id="run", attempt_id=reservation_id, reservation_id=reservation_id, requested=60,
            policy_sha256="a" * 64, recorded_at="2026-07-18T00:00:00Z", **_kwargs(tmp_path),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, competing = list(pool.map(reserve_once, ("one", "two")))
    assert sum(result.allowed for result in (first, competing)) == 1
    winner = first if first.allowed else competing
    retry = runtime.reserve_work_unit_reservation(
        cap=100, run_id="run", attempt_id=winner.receipt["attempt_id"], reservation_id=winner.receipt["reservation_id"], requested=60,
        policy_sha256="a" * 64, recorded_at="2026-07-18T00:00:00Z", **_kwargs(tmp_path),
    )
    assert retry.allowed and retry.persist is False
    assert retry.receipt == winner.receipt


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
            runtime.reserve_work_unit_reservation,
            cap=100, run_id="run", attempt_id="attempt", reservation_id="reservation", requested=10,
            policy_sha256="a" * 64, recorded_at="2026-07-18T00:00:00Z", **_kwargs(tmp_path),
        )
        assert not reservation.done()
        release_generic_record.set()
        generic_result = generic.result(timeout=5)
        reservation_result = reservation.result(timeout=5)
    assert generic_result.sequence == 1
    assert reservation_result.allowed
    verified = runtime.verify(
        side_effect_ledger_root=str(tmp_path / "side-effect-ledger"), active_work_ledger_root=str(awl),
    )
    assert verified.ok, verified.errors
    assert verified.summary["chains"][0]["record_count"] == 2


def test_verified_current_work_unit_binding_requires_serialized_current_ledger_evidence(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    decision = runtime.reserve_work_unit_reservation(
        cap=100, run_id="run", attempt_id="attempt", reservation_id="reservation", requested=10,
        policy_sha256="a" * 64, recorded_at="2026-07-18T00:00:00Z", **_kwargs(tmp_path),
    )
    binding = decision.binding
    assert binding is not None
    evidence = runtime.work_unit_reservation_evidence(
        binding,
        side_effect_ledger_root=tmp_path / "side-effect-ledger", active_work_ledger_root=awl,
        controller_id=CONTROLLER, lane_id=LANE, run_id="run", attempt_id="attempt",
        reservation_id="reservation", policy_sha256="a" * 64,
    )
    assert evidence["valid"]
    assert evidence["receipt_id"] == decision.receipt["receipt_id"]
    assert not runtime.work_unit_reservation_evidence(
        dict(decision.receipt),
        side_effect_ledger_root=tmp_path / "side-effect-ledger", active_work_ledger_root=awl,
        controller_id=CONTROLLER, lane_id=LANE, run_id="run", attempt_id="attempt",
        reservation_id="reservation", policy_sha256="a" * 64,
    )["valid"]
    assert not runtime.work_unit_reservation_evidence(
        binding,
        side_effect_ledger_root=tmp_path / "side-effect-ledger", active_work_ledger_root=awl,
        controller_id=CONTROLLER, lane_id="wrong-lane", run_id="run", attempt_id="attempt",
        reservation_id="reservation", policy_sha256="a" * 64,
    )["valid"]
    _append(tmp_path, effect_id="effect-after-reservation")
    assert not runtime.work_unit_reservation_evidence(
        binding,
        side_effect_ledger_root=tmp_path / "side-effect-ledger", active_work_ledger_root=awl,
        controller_id=CONTROLLER, lane_id=LANE, run_id="run", attempt_id="attempt",
        reservation_id="reservation", policy_sha256="a" * 64,
    )["valid"]


def test_verified_binding_is_opaque_issued_and_rejects_raw_copy_and_substitution(tmp_path: Path):
    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    decision = runtime.reserve_work_unit_reservation(
        cap=100, run_id="run", attempt_id="attempt", reservation_id="reservation", requested=10,
        policy_sha256="a" * 64, recorded_at="2026-07-18T00:00:00Z", **_kwargs(tmp_path),
    )
    binding = decision.binding
    assert binding is not None

    with pytest.raises(TypeError):
        runtime.VerifiedCurrentWorkUnitBinding()
    with pytest.raises(TypeError):
        copy.copy(binding)
    with pytest.raises(TypeError):
        copy.deepcopy(binding)
    with pytest.raises(TypeError):
        replace(binding)
    with pytest.raises(AttributeError):
        binding.run_id = "substituted"
    with pytest.raises(AttributeError):
        _ = binding.__dict__

    raw = runtime.record_work_unit_reservation(receipt=decision.receipt, **_kwargs(tmp_path, effect_id="raw"))
    assert raw.record_sha256
    assert not runtime.work_unit_reservation_evidence(
        object.__new__(runtime.VerifiedCurrentWorkUnitBinding),
        side_effect_ledger_root=tmp_path / "side-effect-ledger", active_work_ledger_root=awl,
        controller_id=CONTROLLER, lane_id=LANE, run_id="run", attempt_id="attempt",
        reservation_id="reservation", policy_sha256="a" * 64,
    )["valid"]


def test_record_is_valid_under_existing_side_effect_ledger_substrate(tmp_path: Path):
    from creator_engine_validator.checks.side_effect_ledger import (
        validate_side_effect_ledger_record,
    )

    awl = tmp_path / ".hermes" / "active-work-ledger"
    _claim(awl)
    result = _append(tmp_path)
    assert validate_side_effect_ledger_record(result.record, result.record_path) == []


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
    _append(tmp_path, effect_id="effect-a", effect_kind="tracked_file_change")
    last = _append(tmp_path, effect_id="effect-b", effect_kind="git_mutation")
    result = runtime.verify(
        side_effect_ledger_root=str(tmp_path / "side-effect-ledger"),
        active_work_ledger_root=str(awl),
    )
    assert result.ok, result.errors
    assert result.summary["record_count"] == 2
    assert result.summary["effect_kind_counts"]["tracked_file_change"] == 1
    assert result.summary["effect_kind_counts"]["git_mutation"] == 1
    chain = result.summary["chains"][0]
    assert chain["head_sha256"] == last.record_sha256
    assert chain["last_record_ref"].endswith("000002-effect-b.json")


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
