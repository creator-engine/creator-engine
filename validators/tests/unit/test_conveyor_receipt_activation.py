from __future__ import annotations

import json
import os
import stat

import pytest

from creator_engine_validator import conveyor_receipt_activation as activation
from creator_engine_validator.conveyor_discovery import ConveyorSeatDiscoveryRunner, HandledSignalReceipt, SeatProbeSpec


SHA = "a" * 40


def _legacy(path, *, seat_id="seat-1", branch="ce-582-activation", sha=SHA):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    raw = json.dumps({"processed": [{"seat_id": seat_id, "branch": branch, "sha": sha}]}, sort_keys=True).encode() + b"\n"
    path.write_bytes(raw)
    path.chmod(0o600)
    return raw


def test_plan_is_non_mutating_and_apply_seals_terminal_so_signal_cannot_reenter(tmp_path):
    state = tmp_path / "state" / "processed.json"
    legacy = _legacy(state)
    before = state.stat()

    planned = activation.plan(state)

    assert state.read_bytes() == legacy
    assert (state.stat().st_dev, state.stat().st_ino) == (before.st_dev, before.st_ino)
    assert planned.migrated_receipts[0]["completion_sealed"] is True
    assert activation.apply(state, accept_plan_sha=planned.sha256) == planned
    assert stat.S_IMODE(state.stat().st_mode) == 0o600
    assert (tmp_path / "state" / planned.backup_name).read_bytes() == legacy
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))], state,
        probe_runner=lambda _argv: f"READY-FOR-HARVEST ce-582-activation {SHA}",
    )
    payload = list(runner())[0]
    receipt = HandledSignalReceipt(state, payload.receipt_identity.seat_id, payload.receipt_identity.branch, payload.receipt_identity.sha)
    assert receipt.claim() is False


def test_normal_discovery_refuses_legacy_without_logging_payload_or_mutating(tmp_path):
    state = tmp_path / "private" / "processed.json"
    sentinel = "TOP-SECRET-RECEIPT-PAYLOAD"
    raw = json.dumps({"processed": [{"seat_id": sentinel, "branch": "ce-582-activation", "sha": SHA}]}).encode()
    state.parent.mkdir(mode=0o700)
    state.write_bytes(raw)
    state.chmod(0o600)
    audit = []
    runner = ConveyorSeatDiscoveryRunner([SeatProbeSpec("seat-1", ("probe",))], state, probe_runner=lambda _argv: f"READY-FOR-HARVEST ce-582-activation {SHA}", audit_sink=audit.append)

    assert list(runner()) == []
    assert state.read_bytes() == raw
    assert sentinel not in str(audit)
    assert audit[-1]["reason"] == "corrupt_receipt_state"


def test_stale_plan_and_swapped_legacy_refuse_before_mutation(tmp_path):
    state = tmp_path / "private" / "processed.json"
    original = _legacy(state)
    planned = activation.plan(state)
    replacement = state.parent / "replacement.json"
    _legacy(replacement, sha="b" * 40)
    os.replace(replacement, state)

    with pytest.raises(activation.ReceiptActivationRefused, match="activation_plan_changed"):
        activation.apply(state, accept_plan_sha=planned.sha256)
    assert json.loads(state.read_text())["processed"][0]["sha"] == "b" * 40
    assert not list(state.parent.glob("*.bak"))
    assert original != state.read_bytes()


def test_rollback_restores_exact_legacy_and_normal_discovery_refuses_again(tmp_path):
    state = tmp_path / "private" / "processed.json"
    raw = _legacy(state)
    planned = activation.plan(state)
    activation.apply(state, accept_plan_sha=planned.sha256)

    activation.rollback(state, accept_plan_sha=planned.sha256)

    assert state.read_bytes() == raw
    runner = ConveyorSeatDiscoveryRunner([SeatProbeSpec("seat-1", ("probe",))], state, probe_runner=lambda _argv: f"READY-FOR-HARVEST ce-582-activation {SHA}")
    assert list(runner()) == []


def test_apply_restores_legacy_when_v1_publication_fails_after_backup_rename(tmp_path, monkeypatch):
    state = tmp_path / "private" / "processed.json"
    raw = _legacy(state)
    planned = activation.plan(state)

    def fail_v1_publication(*_args, **_kwargs):
        raise OSError("injected v1 temporary-file failure")

    monkeypatch.setattr(activation.receipt, "_write_receipt_state", fail_v1_publication)

    with pytest.raises(activation.receipt.ReceiptPersistenceError, match="receipt_state_persistence_failed"):
        activation.apply(state, accept_plan_sha=planned.sha256)

    assert state.read_bytes() == raw
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))], state,
        probe_runner=lambda _argv: f"READY-FOR-HARVEST ce-582-activation {SHA}",
    )
    assert list(runner()) == []


def test_apply_resumes_only_its_byte_identical_orphaned_backup(tmp_path):
    state = tmp_path / "private" / "processed.json"
    raw = _legacy(state)
    planned = activation.plan(state)

    with activation.receipt._locked_receipt_directory(state) as (location, _lock_fd, _lock_metadata):
        activation._write_backup(location, planned.backup_name, raw)

    assert activation.apply(state, accept_plan_sha=planned.sha256) == planned
    assert (state.parent / planned.backup_name).read_bytes() == raw


def test_rollback_refuses_when_v1_ledger_diverged_from_migrated_set(tmp_path):
    state = tmp_path / "private" / "processed.json"
    _legacy(state)
    planned = activation.plan(state)
    activation.apply(state, accept_plan_sha=planned.sha256)
    state.write_text('{"version": 1, "receipts": []}\n', encoding="utf-8")
    state.chmod(0o600)

    with pytest.raises(activation.ReceiptActivationRefused, match="rollback_receipt_state_diverged"):
        activation.rollback(state, accept_plan_sha=planned.sha256)
    assert (state.parent / planned.backup_name).exists()


def test_rollback_malformed_v1_state_is_structured_refusal(tmp_path, capsys):
    state = tmp_path / "private" / "processed.json"
    _legacy(state)
    planned = activation.plan(state)
    activation.apply(state, accept_plan_sha=planned.sha256)
    state.write_text('{"version": 1, "receipts": "not-a-list"}\n', encoding="utf-8")
    state.chmod(0o600)

    assert activation.main([str(state), "rollback", "--accept-plan-sha", planned.sha256]) == 2
    assert "rollback_receipt_state_invalid" in capsys.readouterr().err


def test_malformed_legacy_refuses_without_mutation(tmp_path):
    state = tmp_path / "private" / "processed.json"
    state.parent.mkdir(mode=0o700)
    state.write_text('{"processed":["not-a-tuple"]}', encoding="utf-8")
    state.chmod(0o600)
    raw = state.read_bytes()

    with pytest.raises(activation.ReceiptActivationRefused, match="legacy_receipt_entry_invalid"):
        activation.plan(state)
    assert state.read_bytes() == raw


def test_cli_requires_explicit_apply_plan_sha(tmp_path, capsys):
    state = tmp_path / "private" / "processed.json"
    _legacy(state)

    assert activation.main([str(state), "apply"]) == 2
    assert "activation_plan_sha_required" in capsys.readouterr().err
