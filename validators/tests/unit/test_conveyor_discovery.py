from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from creator_engine_validator import conveyor_discovery
from creator_engine_validator.conveyor_daemon import ConveyorDaemonItem
from creator_engine_validator.conveyor_discovery import (
    ConveyorSeatDiscoveryRunner,
    HandledSignalReceipt,
    ReadyForHarvestSignal,
    ReceiptIdentity,
    SeatProbeSpec,
    parse_ready_for_harvest_signals,
)
from creator_engine_validator.pickup_payload_schema import validate_discovery_payload

SHA_ONE = "a" * 40
SHA_TWO = "b" * 40
SHA_THREE = "c" * 40


def _receipt_for_payload(state_path, payload):
    identity = payload.receipt_identity
    return HandledSignalReceipt(state_path, identity.seat_id, identity.branch, identity.sha)


def _write_private_ledger(state_path: Path, content: str) -> None:
    state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    state_path.parent.chmod(0o700)
    state_path.write_text(content, encoding="utf-8")
    state_path.chmod(0o600)


def test_seat_probe_spec_stores_argv_as_tuple():
    spec = SeatProbeSpec("seat-1", ["tmux", "capture-pane", "-p"])

    assert spec.argv == ("tmux", "capture-pane", "-p")

    with pytest.raises(AttributeError):
        spec.seat_id = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("pane_text", "branch", "sha", "tag"),
    [
        (f"\x1b[32m• READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE} done\x1b[0m", "ce-388-conveyor-discovery", SHA_ONE, "done"),
        (f"- READY-FOR-HARVEST ce-389-wrapped\n  {SHA_TWO}", "ce-389-wrapped", SHA_TWO, None),
        (f"> READY-FOR-HARVEST ce-390-marker {SHA_THREE}", "ce-390-marker", SHA_THREE, None),
    ],
)
def test_parse_tolerates_bullets_ansi_markers_and_wrapping(
    pane_text: str,
    branch: str,
    sha: str,
    tag: str | None,
):
    assert parse_ready_for_harvest_signals(pane_text) == (
        ReadyForHarvestSignal(branch=branch, sha=sha, tag=tag),
    )


@pytest.mark.parametrize(
    ("pane_text", "sha", "tag"),
    [
        (
            f"  READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE} REWORK",
            SHA_ONE,
            "REWORK",
        ),
        (
            f"• READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_TWO} REWORK-2",
            SHA_TWO,
            "REWORK-2",
        ),
    ],
)
def test_parse_accepts_rework_and_rework_n_suffixes(
    pane_text: str,
    sha: str,
    tag: str,
):
    assert parse_ready_for_harvest_signals(pane_text) == (
        ReadyForHarvestSignal(branch="ce-388-conveyor-discovery", sha=sha, tag=tag),
    )


def test_placeholder_and_diff_echoes_are_rejected_and_audited():
    audit: list[dict] = []
    pane_text = "\n".join(
        [
            "READY-FOR-HARVEST ce-437-portability-guard <sha>",
            "READY-FOR-HARVEST ce-437-portability-guard <new-sha>",
            "+READY-FOR-HARVEST ce-437-portability-guard " + SHA_ONE,
            "42 +READY-FOR-HARVEST ce-437-portability-guard " + SHA_TWO,
            "43+READY-FOR-HARVEST ce-437-portability-guard " + SHA_THREE,
        ]
    )

    signals = parse_ready_for_harvest_signals(
        pane_text,
        audit_sink=lambda record: audit.append(dict(record)),
        seat_id="seat-a",
    )

    assert signals == ()
    assert [record["reason"] for record in audit] == [
        "bad_sha",
        "bad_sha",
        "diff_echo",
        "diff_echo",
        "diff_echo",
    ]
    assert audit[0]["detail"] == "placeholder_sha"
    assert audit[1]["detail"] == "placeholder_sha"
    assert "READY-FOR-HARVEST ce-437-portability-guard <sha>" not in str(audit)


def test_ready_token_in_arbitrary_prose_is_rejected_even_with_valid_sha():
    audit: list[dict] = []
    pane_text = f"Instruction echo: READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}"

    signals = parse_ready_for_harvest_signals(
        pane_text,
        audit_sink=lambda record: audit.append(dict(record)),
        seat_id="seat-a",
    )

    assert signals == ()
    assert audit == [
        {
            "action": "conveyor_discovery_rejected",
            "source": "conveyor_discovery",
            "reason": "non_signal_ready_echo",
            "seat_id": "seat-a",
            "line_number": 1,
        }
    ]


def test_last_signal_wins_per_branch():
    pane_text = "\n".join(
        [
            f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
            f"READY-FOR-HARVEST ce-389-other {SHA_THREE}",
            f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_TWO}",
        ]
    )

    signals = parse_ready_for_harvest_signals(pane_text)

    assert signals == (
        ReadyForHarvestSignal(branch="ce-388-conveyor-discovery", sha=SHA_TWO),
        ReadyForHarvestSignal(branch="ce-389-other", sha=SHA_THREE),
    )


def test_runner_receipts_are_versioned_and_only_one_duplicate_is_processable(tmp_path):
    state_path = tmp_path / "processed.json"
    spec = SeatProbeSpec("seat-1", ("probe", "seat-1"))
    pane_text = f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}"

    runner = ConveyorSeatDiscoveryRunner(
        [spec],
        state_path,
        probe_runner=lambda argv: pane_text,
    )

    first = list(runner())
    assert _receipt_for_payload(state_path, first[0]).claim() is True
    second = list(runner())

    assert len(first) == 1
    assert len(second) == 1
    assert _receipt_for_payload(state_path, second[0]).claim() is False
    assert first[0]["branch_name"] == "ce-388-conveyor-discovery"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state == {
        "receipts": [
            {
                "seat_id": "seat-1",
                "branch": "ce-388-conveyor-discovery",
                "sha": SHA_ONE,
                "state": "processing",
            }
        ],
        "version": 1,
    }
    assert not list(tmp_path.glob("*.tmp"))


def test_corrupt_receipt_state_is_preserved_and_refused(tmp_path):
    state_path = tmp_path / "processed.json"
    _write_private_ledger(state_path, "{not json")
    audit: list[dict] = []
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
        audit_sink=lambda record: audit.append(dict(record)),
    )

    payloads = list(runner())

    assert payloads == []
    assert any(record["reason"] == "corrupt_receipt_state" for record in audit)
    assert state_path.read_text(encoding="utf-8") == "{not json"


def test_receipt_transitions_are_monotonic_and_new_sha_is_separate(tmp_path):
    state_path = tmp_path / "receipts.json"
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
    )
    first = _receipt_for_payload(state_path, list(runner())[0])
    assert first.claim() is True
    assert first.complete("failed") is True
    assert first.claim() is False
    assert first.complete("pr_opened") is False

    next_runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_TWO}",
    )
    second = _receipt_for_payload(state_path, list(next_runner())[0])
    assert second.claim() is True
    assert second.complete("uncertain") is True
    assert {(entry["sha"], entry["state"]) for entry in json.loads(state_path.read_text())["receipts"]} == {
        (SHA_ONE, "failed"),
        (SHA_TWO, "uncertain"),
    }


def test_new_sha_is_processable_while_prior_receipt_is_unfinished(tmp_path):
    state_path = tmp_path / "receipts.json"
    first_payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
        )()
    )[0]
    first = _receipt_for_payload(state_path, first_payload)
    assert first.claim() is True

    second_payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_TWO}",
        )()
    )[0]
    second = _receipt_for_payload(state_path, second_payload)

    assert second.claim() is True
    assert {(entry["sha"], entry["state"]) for entry in json.loads(state_path.read_text())["receipts"]} == {
        (SHA_ONE, "processing"),
        (SHA_TWO, "processing"),
    }


def test_receipt_lock_failure_fails_closed_and_preserves_state(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    receipt = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, receipt)
    original = state_path.read_text(encoding="utf-8")

    def fail_lock(*_args):
        raise PermissionError("lock denied")

    monkeypatch.setattr(conveyor_discovery.fcntl, "flock", fail_lock)

    with pytest.raises(conveyor_discovery.ReceiptPersistenceError, match="receipt_state_persistence_failed"):
        receipt.claim()

    assert state_path.read_text(encoding="utf-8") == original


def test_receipt_replace_failure_fails_closed_and_preserves_state(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    receipt = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, receipt)
    original = state_path.read_text(encoding="utf-8")

    def fail_replace(*_args, **_kwargs):
        raise OSError("replace denied")

    monkeypatch.setattr(conveyor_discovery.os, "replace", fail_replace)

    with pytest.raises(conveyor_discovery.ReceiptPersistenceError, match="receipt_state_write_failed"):
        receipt.claim()

    assert state_path.read_text(encoding="utf-8") == original
    assert not list(tmp_path.glob("*.tmp"))


def test_concurrent_claims_have_one_winner_and_atomic_json(tmp_path):
    state_path = tmp_path / "receipts.json"
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
    )
    receipt = _receipt_for_payload(state_path, list(runner())[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _ignored: receipt.claim(), range(2)))

    assert claims.count(True) == 1
    assert json.loads(state_path.read_text())["receipts"][0]["state"] == "processing"


def test_emitted_payload_passes_schema_and_daemon_mapping(tmp_path):
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        tmp_path / "state.json",
        probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
    )

    payload = list(runner())[0]

    assert set(payload) == {"issue", "branch_name", "pr_title", "pr_body"}
    assert validate_discovery_payload(payload).to_dict() == payload
    assert payload.receipt_identity == ReceiptIdentity("seat-1", "ce-388-conveyor-discovery", SHA_ONE)
    assert not hasattr(payload, "receipt")
    assert not hasattr(payload.receipt_identity, "state_path")
    item = ConveyorDaemonItem.from_mapping(payload)
    assert item.branch == "ce-388-conveyor-discovery"
    assert item.issue == "388"
    assert SHA_ONE in payload["pr_body"]


def test_receipt_state_fsyncs_parent_directory_after_replace(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    events: list[str] = []
    real_replace = conveyor_discovery.os.replace
    real_fsync = conveyor_discovery.os.fsync

    def record_replace(source, target, **kwargs):
        events.append("replace")
        return real_replace(source, target, **kwargs)

    def record_fsync(fd):
        metadata = os.fstat(fd)
        events.append("directory-fsync" if stat.S_ISDIR(metadata.st_mode) else "file-fsync")
        return real_fsync(fd)

    monkeypatch.setattr(conveyor_discovery.os, "replace", record_replace)
    monkeypatch.setattr(conveyor_discovery.os, "fsync", record_fsync)

    assert receipt.claim() is True

    assert events == [
        "file-fsync",
        "directory-fsync",
        "file-fsync",
        "directory-fsync",
        "replace",
        "directory-fsync",
    ]


def test_receipt_parent_fsync_failure_refuses_write_and_cleans_temp(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    real_fsync = conveyor_discovery.os.fsync
    directory_fsyncs = 0

    def fail_parent_fsync(fd):
        nonlocal directory_fsyncs
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            directory_fsyncs += 1
        if directory_fsyncs == 2:
            raise OSError("directory fsync denied")
        return real_fsync(fd)

    monkeypatch.setattr(conveyor_discovery.os, "fsync", fail_parent_fsync)

    with pytest.raises(conveyor_discovery.ReceiptPersistenceError):
        receipt.claim()

    assert not list(tmp_path.glob("*.tmp"))
    assert json.loads(state_path.read_text())["receipts"][0]["state"] == "observed"


def test_receipt_temp_fsync_failure_refuses_write_and_cleans_temp(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    real_fsync = conveyor_discovery.os.fsync

    regular_fsyncs = 0

    def fail_temp_fsync(fd):
        nonlocal regular_fsyncs
        if stat.S_ISREG(os.fstat(fd).st_mode):
            regular_fsyncs += 1
            if regular_fsyncs == 2:
                raise OSError("temp fsync denied")
        return real_fsync(fd)

    monkeypatch.setattr(conveyor_discovery.os, "fsync", fail_temp_fsync)

    with pytest.raises(conveyor_discovery.ReceiptPersistenceError):
        receipt.claim()

    assert not list(tmp_path.glob("*.tmp"))
    assert json.loads(state_path.read_text())["receipts"][0]["state"] == "observed"


def test_completion_writes_one_sealed_terminal_after_claim(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    receipt = _receipt_for_payload(
        state_path,
        list(
            ConveyorSeatDiscoveryRunner(
                [SeatProbeSpec("seat-1", ("probe",))],
                state_path,
                probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
            )()
        )[0],
    )
    assert receipt.claim() is True
    writes: list[list[dict[str, object]]] = []
    real_write = conveyor_discovery._write_receipt_state

    def record_write(location, entries, expected):
        writes.append([dict(entry) for entry in entries])
        return real_write(location, entries, expected)

    monkeypatch.setattr(conveyor_discovery, "_write_receipt_state", record_write)

    assert receipt.complete("pr_opened") is True
    assert writes == [
        [
            {
                "seat_id": "seat-1",
                "branch": "ce-388-conveyor-discovery",
                "sha": SHA_ONE,
                "state": "pr_opened",
                "completion_sealed": True,
            }
        ]
    ]


def test_terminal_seal_parent_fsync_failure_leaves_visible_seal_and_audits(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    receipt = _receipt_for_payload(
        state_path,
        list(
            ConveyorSeatDiscoveryRunner(
                [SeatProbeSpec("seat-1", ("probe",))],
                state_path,
                probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
            )()
        )[0],
    )
    assert receipt.claim() is True
    real_fsync = conveyor_discovery.os.fsync
    directory_fsyncs = 0

    def fail_sealed_terminal_parent_fsync(fd):
        nonlocal directory_fsyncs
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            directory_fsyncs += 1
            if directory_fsyncs == 3:
                raise OSError("terminal directory fsync denied")
        return real_fsync(fd)

    monkeypatch.setattr(conveyor_discovery.os, "fsync", fail_sealed_terminal_parent_fsync)

    with pytest.raises(conveyor_discovery.ReceiptDurabilityUncertainError):
        receipt.complete("pr_opened")

    assert json.loads(state_path.read_text())["receipts"][0]["completion_sealed"] is True
    audits: list[dict[str, object]] = []
    restarted = HandledSignalReceipt(
        state_path, "seat-1", "ce-388-conveyor-discovery", SHA_ONE, audit_sink=audits.append
    )
    assert restarted.claim() is False
    assert audits == [
        {
            "action": "conveyor_discovery_rejected",
            "source": "conveyor_discovery",
            "reason": "receipt_terminal_sealed",
            "receipt_fingerprint": conveyor_discovery._receipt_fingerprint(restarted),
        }
    ]


def test_terminal_seal_replace_failure_leaves_processing_and_audits_recovery(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    receipt = _receipt_for_payload(
        state_path,
        list(
            ConveyorSeatDiscoveryRunner(
                [SeatProbeSpec("seat-1", ("probe",))],
                state_path,
                probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
            )()
        )[0],
    )
    assert receipt.claim() is True

    def fail_replace(*_args, **_kwargs):
        raise OSError("terminal replace denied")

    monkeypatch.setattr(conveyor_discovery.os, "replace", fail_replace)
    with pytest.raises(conveyor_discovery.ReceiptPersistenceError):
        receipt.complete("pr_opened")

    assert json.loads(state_path.read_text())["receipts"][0]["state"] == "processing"
    audits: list[dict[str, object]] = []
    restarted = HandledSignalReceipt(
        state_path, "seat-1", "ce-388-conveyor-discovery", SHA_ONE, audit_sink=audits.append
    )
    assert restarted.claim() is False
    assert audits[0]["reason"] == "receipt_processing_recovery_required"
    assert "seat-1" not in str(audits)
    assert "ce-388-conveyor-discovery" not in str(audits)
    assert SHA_ONE not in str(audits)


@pytest.mark.parametrize(
    ("entry", "error"),
    [
        ({"state": "processing", "completion_sealed": True}, "receipt_completion_sealed_invalid"),
        ({"state": "failed", "completion_sealed": False}, "receipt_completion_sealed_invalid"),
        (
            {"state": "failed", "completion_sealed": True, "completion_pending": True},
            "receipt_completion_markers_conflict",
        ),
    ],
)
def test_receipt_validation_rejects_invalid_completion_seal_markers(entry, error):
    with pytest.raises(ValueError, match=error):
        conveyor_discovery._receipt_entries(
            {
                "version": 1,
                "receipts": [
                    {
                        "seat_id": "seat-1",
                        "branch": "ce-388-conveyor-discovery",
                        "sha": SHA_ONE,
                        **entry,
                    }
                ],
            }
        )


def test_legacy_pending_processing_receipt_remains_fail_closed(tmp_path):
    state_path = tmp_path / "receipts.json"
    _write_private_ledger(
        state_path,
        json.dumps(
            {
                "version": 1,
                "receipts": [
                    {
                        "seat_id": "seat-1",
                        "branch": "ce-388-conveyor-discovery",
                        "sha": SHA_ONE,
                        "state": "processing",
                        "completion_pending": True,
                    }
                ],
            }
        ),
    )
    audits: list[dict[str, object]] = []
    receipt = HandledSignalReceipt(
        state_path, "seat-1", "ce-388-conveyor-discovery", SHA_ONE, audit_sink=audits.append
    )

    assert receipt.complete("failed") is False
    assert receipt.claim() is False
    assert audits[0]["reason"] == "receipt_terminal_durability_unproven"


@pytest.mark.parametrize(
    "raw",
    ["relative/receipts.json", "/", "/tmp/./receipts.json", "/tmp/../receipts.json", "/tmp/x\x00y"],
)
def test_receipt_state_path_is_validated_lexically_without_resolution(raw):
    with pytest.raises(conveyor_discovery.ReceiptPersistenceError, match="receipt_state_path_invalid"):
        ConveyorSeatDiscoveryRunner([], raw)


def test_component_symlink_and_leaf_symlink_fail_closed_without_outside_mutation(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    canary = outside / "canary"
    canary.write_text("unchanged", encoding="utf-8")
    (tmp_path / "component").symlink_to(outside, target_is_directory=True)

    component_runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        tmp_path / "component" / "private" / "receipts.json",
        probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
    )
    assert list(component_runner()) == []

    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    ledger_target = outside / "ledger"
    ledger_target.write_text("outside", encoding="utf-8")
    ledger_target.chmod(0o600)
    (private / "receipts.json").symlink_to(ledger_target)
    leaf_runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        private / "receipts.json",
        probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
    )
    assert list(leaf_runner()) == []
    assert canary.read_text(encoding="utf-8") == "unchanged"
    assert ledger_target.read_text(encoding="utf-8") == "outside"


def test_component_swap_before_publication_does_not_mutate_replacement_tree(tmp_path, monkeypatch):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    state_path = private / "receipts.json"
    moved = tmp_path / "moved-private"
    calls = 0
    real_rewalk = conveyor_discovery._SecureReceiptDirectory.rewalk

    def swap_before_publication(location):
        nonlocal calls
        calls += 1
        if calls == 3:
            private.rename(moved)
            private.mkdir(mode=0o700)
            (private / "canary").write_text("replacement", encoding="utf-8")
        return real_rewalk(location)

    monkeypatch.setattr(conveyor_discovery._SecureReceiptDirectory, "rewalk", swap_before_publication)
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
    )

    assert list(runner()) == []
    assert (private / "canary").read_text(encoding="utf-8") == "replacement"
    assert not (private / "receipts.json").exists()
    assert not list(moved.glob("*.tmp"))


def test_receipt_syscall_guard_refuses_without_replace_dirfd_support(monkeypatch):
    """Publication uses replaceat, so the platform guard must require it."""

    original = os.supports_dir_fd
    monkeypatch.setattr(
        os,
        "supports_dir_fd",
        frozenset(function for function in original if function is not os.rename),
    )

    assert os.replace in conveyor_discovery._RECEIPT_DIR_FD_SYSCALLS
    assert conveyor_discovery._receipt_syscalls_supported() is False


@pytest.mark.parametrize("mask", [0o000, 0o077])
def test_writer_created_directory_lock_temp_and_ledger_have_exact_private_modes(tmp_path, mask):
    state_path = tmp_path / "private" / "receipts.json"
    prior = os.umask(mask)
    try:
        payloads = list(
            ConveyorSeatDiscoveryRunner(
                [SeatProbeSpec("seat-1", ("probe",))],
                state_path,
                probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
            )()
        )
    finally:
        os.umask(prior)

    assert len(payloads) == 1
    assert stat.S_IMODE(state_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600
    assert stat.S_IMODE((state_path.parent / ".receipts.json.lock").stat().st_mode) == 0o600
    assert not list(state_path.parent.glob("*.tmp"))


def test_existing_unsafe_directory_file_and_hardlink_are_refused_without_repair(tmp_path):
    unsafe_dir = tmp_path / "unsafe"
    unsafe_dir.mkdir(mode=0o755)
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        unsafe_dir / "receipts.json",
        probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
    )
    assert list(runner()) == []
    assert stat.S_IMODE(unsafe_dir.stat().st_mode) == 0o755

    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    state_path = private / "receipts.json"
    _write_private_ledger(state_path, '{"version":1,"receipts":[]}')
    state_path.chmod(0o644)
    assert list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    ) == []
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o644

    state_path.chmod(0o600)
    hardlink = private / "ledger-hardlink"
    os.link(state_path, hardlink)
    assert list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    ) == []
    assert state_path.stat().st_nlink == 2


def test_wrong_daemon_owner_identity_fails_before_private_tree_mutation(tmp_path, monkeypatch):
    state_path = tmp_path / "private" / "receipts.json"
    monkeypatch.setattr(conveyor_discovery.os, "geteuid", lambda: os.getuid() + 1)
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
    )
    assert list(runner()) == []
    assert not state_path.parent.exists()


def test_mkdir_eexist_race_never_chmods_foreign_directory(tmp_path, monkeypatch):
    state_path = tmp_path / "private" / "receipts.json"
    real_mkdir = conveyor_discovery.os.mkdir

    def race_mkdir(name, mode=0o777, *, dir_fd=None):
        if name == "private" and dir_fd is not None:
            real_mkdir(name, 0o755, dir_fd=dir_fd)
            raise FileExistsError(name)
        return real_mkdir(name, mode, dir_fd=dir_fd)

    monkeypatch.setattr(conveyor_discovery.os, "mkdir", race_mkdir)
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
    )
    assert list(runner()) == []
    assert stat.S_IMODE(state_path.parent.stat().st_mode) == 0o755


def test_lock_eexist_race_never_chmods_or_cleans_foreign_lock(tmp_path):
    state_path = tmp_path / "receipts.json"
    lock_path = tmp_path / ".receipts.json.lock"
    lock_path.write_text("foreign", encoding="utf-8")
    lock_path.chmod(0o644)
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
    )
    assert list(runner()) == []
    assert lock_path.read_text(encoding="utf-8") == "foreign"
    assert stat.S_IMODE(lock_path.stat().st_mode) == 0o644


def test_lock_name_substitution_after_acquisition_never_mutates_foreign_object(
    tmp_path, monkeypatch
):
    state_path = tmp_path / "receipts.json"
    lock_path = tmp_path / ".receipts.json.lock"
    displaced_lock = tmp_path / "displaced-lock"
    real_flock = conveyor_discovery.fcntl.flock
    substituted = False

    def substitute_after_acquisition(fd, operation):
        nonlocal substituted
        result = real_flock(fd, operation)
        if operation == conveyor_discovery.fcntl.LOCK_EX and not substituted:
            substituted = True
            lock_path.rename(displaced_lock)
            lock_path.write_text("foreign-lock-canary", encoding="utf-8")
            lock_path.chmod(0o600)
        return result

    monkeypatch.setattr(conveyor_discovery.fcntl, "flock", substitute_after_acquisition)
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
    )

    assert list(runner()) == []
    assert lock_path.read_text(encoding="utf-8") == "foreign-lock-canary"
    assert displaced_lock.exists()
    assert not state_path.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_read_and_encoded_ledger_boundaries_accept_maximum_and_reject_first_extra_byte(
    tmp_path, monkeypatch
):
    receipt = {
        "seat_id": "seat-1",
        "branch": "b",
        "sha": SHA_ONE,
        "state": "observed",
    }
    maximum = conveyor_discovery._encoded_receipt_state([receipt])
    first_rejected = conveyor_discovery._encoded_receipt_state(
        [{**receipt, "branch": "bb"}]
    )
    assert len(first_rejected) == len(maximum) + 1
    monkeypatch.setattr(conveyor_discovery, "_MAX_LEDGER_BYTES", len(maximum))

    assert conveyor_discovery._encoded_receipt_state([receipt]) == maximum
    with pytest.raises(
        conveyor_discovery.ReceiptPersistenceError, match="receipt_state_too_large"
    ):
        conveyor_discovery._encoded_receipt_state([{**receipt, "branch": "bb"}])

    ledger_path = tmp_path / "boundary-ledger"
    ledger_path.write_bytes(maximum)
    fd = os.open(ledger_path, os.O_RDONLY)
    try:
        assert conveyor_discovery._read_all(fd) == maximum
    finally:
        os.close(fd)
    ledger_path.write_bytes(maximum + b"x")
    fd = os.open(ledger_path, os.O_RDONLY)
    try:
        with pytest.raises(
            conveyor_discovery.ReceiptPersistenceError, match="receipt_state_too_large"
        ):
            conveyor_discovery._read_all(fd)
    finally:
        os.close(fd)


def test_readable_maximum_ledger_rejects_larger_encoding_before_temp_and_preserves_bytes(
    tmp_path, monkeypatch
):
    state_path = tmp_path / "receipts.json"
    existing = {
        "seat_id": "seat-1",
        "branch": "existing-branch",
        "sha": SHA_ONE,
        "state": "observed",
    }
    original = conveyor_discovery._encoded_receipt_state([existing])
    _write_private_ledger(state_path, original.decode("utf-8"))
    monkeypatch.setattr(conveyor_discovery, "_MAX_LEDGER_BYTES", len(original))

    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-2", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST added-branch {SHA_TWO}",
    )

    assert list(runner()) == []
    assert state_path.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp"))


def test_temp_name_collision_is_retried_without_touching_foreign_file(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    collision = tmp_path / ".receipts.json.collision.tmp"
    collision.write_text("foreign", encoding="utf-8")
    collision.chmod(0o600)
    names = iter(("collision", "writer"))
    monkeypatch.setattr(conveyor_discovery.secrets, "token_hex", lambda _size: next(names))

    payloads = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    )
    assert len(payloads) == 1
    assert collision.read_text(encoding="utf-8") == "foreign"


@pytest.mark.parametrize("behavior", ["short", "zero", "error"])
def test_write_loop_handles_short_zero_and_error_writes(tmp_path, monkeypatch, behavior):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    real_write = conveyor_discovery.os.write
    calls = 0

    def injected_write(fd, data):
        nonlocal calls
        calls += 1
        if calls == 1 and behavior == "short":
            return real_write(fd, data[:1])
        if calls == 1 and behavior == "zero":
            return 0
        if calls == 1 and behavior == "error":
            raise OSError("injected write error")
        return real_write(fd, data)

    monkeypatch.setattr(conveyor_discovery.os, "write", injected_write)
    if behavior == "short":
        assert receipt.claim() is True
        assert json.loads(state_path.read_text())["receipts"][0]["state"] == "processing"
    else:
        with pytest.raises(conveyor_discovery.ReceiptPersistenceError):
            receipt.claim()
        assert json.loads(state_path.read_text())["receipts"][0]["state"] == "observed"
        assert not list(tmp_path.glob("*.tmp"))


def test_replace_before_action_is_persistence_failure_and_cleans_only_created_temp(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    original = state_path.read_bytes()
    monkeypatch.setattr(
        conveyor_discovery.os,
        "replace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("before replace")),
    )
    with pytest.raises(conveyor_discovery.ReceiptPersistenceError):
        receipt.claim()
    assert state_path.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp"))


def test_real_replace_then_raise_is_uncertain_and_preserves_published_ledger(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    real_replace = conveyor_discovery.os.replace

    def replace_then_raise(*args, **kwargs):
        real_replace(*args, **kwargs)
        raise OSError("ambiguous replace")

    monkeypatch.setattr(conveyor_discovery.os, "replace", replace_then_raise)
    with pytest.raises(conveyor_discovery.ReceiptDurabilityUncertainError):
        receipt.claim()
    assert json.loads(state_path.read_text())["receipts"][0]["state"] == "processing"
    assert not list(tmp_path.glob("*.tmp"))


def test_final_reopen_fault_is_uncertain_and_preserves_published_ledger(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    real_open = conveyor_discovery.os.open
    ledger_reads = 0

    def fail_readback(path, flags, *args, **kwargs):
        nonlocal ledger_reads
        if path == state_path.name and flags & os.O_ACCMODE == os.O_RDONLY:
            ledger_reads += 1
            if ledger_reads == 2:
                raise OSError("readback denied")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(conveyor_discovery.os, "open", fail_readback)
    with pytest.raises(conveyor_discovery.ReceiptDurabilityUncertainError):
        receipt.claim()
    assert json.loads(state_path.read_text())["receipts"][0]["state"] == "processing"


def test_two_concurrent_completions_have_one_winner_and_monotonic_json(tmp_path):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    assert receipt.claim() is True
    with ThreadPoolExecutor(max_workers=2) as pool:
        completions = list(pool.map(receipt.complete, ("failed", "uncertain")))
    assert completions.count(True) == 1
    entry = json.loads(state_path.read_text())["receipts"][0]
    assert entry["state"] in {"failed", "uncertain"}
    assert entry["completion_sealed"] is True


def test_new_private_directory_parent_fsync_failure_fails_closed_before_lock(tmp_path, monkeypatch):
    state_path = tmp_path / "private" / "receipts.json"
    real_fsync = conveyor_discovery.os.fsync
    calls = 0

    def fail_parent_fsync(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("new directory parent fsync denied")
        return real_fsync(fd)

    monkeypatch.setattr(conveyor_discovery.os, "fsync", fail_parent_fsync)
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
    )
    assert list(runner()) == []
    assert stat.S_IMODE(state_path.parent.stat().st_mode) == 0o700
    assert not (state_path.parent / ".receipts.json.lock").exists()


def test_new_lock_file_fsync_failure_preserves_exact_private_lock_and_no_ledger(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    real_fsync = conveyor_discovery.os.fsync

    def fail_lock_fsync(fd):
        if stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("lock fsync denied")
        return real_fsync(fd)

    monkeypatch.setattr(conveyor_discovery.os, "fsync", fail_lock_fsync)
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        state_path,
        probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
    )
    assert list(runner()) == []
    lock_path = tmp_path / ".receipts.json.lock"
    assert stat.S_IMODE(lock_path.stat().st_mode) == 0o600
    assert not state_path.exists()


def test_unlock_fault_after_publication_is_uncertain_and_preserves_terminal(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    assert receipt.claim() is True
    real_flock = conveyor_discovery.fcntl.flock

    def fail_unlock(fd, operation):
        if operation == conveyor_discovery.fcntl.LOCK_UN:
            raise OSError("unlock denied")
        return real_flock(fd, operation)

    monkeypatch.setattr(conveyor_discovery.fcntl, "flock", fail_unlock)
    with pytest.raises(conveyor_discovery.ReceiptDurabilityUncertainError):
        receipt.complete("pr_opened")
    entry = json.loads(state_path.read_text())["receipts"][0]
    assert entry["state"] == "pr_opened"
    assert entry["completion_sealed"] is True


def test_close_fault_after_replace_is_uncertain_and_preserves_terminal(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    assert receipt.claim() is True
    real_close = conveyor_discovery.os.close
    ledger_closes = 0

    def fail_second_nonempty_file_close(fd):
        nonlocal ledger_closes
        metadata = os.fstat(fd)
        if stat.S_ISREG(metadata.st_mode) and metadata.st_size:
            ledger_closes += 1
            if ledger_closes == 2:
                real_close(fd)
                raise OSError("close result lost")
        return real_close(fd)

    monkeypatch.setattr(conveyor_discovery.os, "close", fail_second_nonempty_file_close)
    with pytest.raises(conveyor_discovery.ReceiptDurabilityUncertainError):
        receipt.complete("pr_opened")
    assert json.loads(state_path.read_text())["receipts"][0]["state"] == "pr_opened"


def test_temp_close_fault_does_not_hide_active_primary_or_leave_partial_publication(
    tmp_path, monkeypatch
):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-private-coordinate", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST secret-branch {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    original = state_path.read_bytes()
    real_write = conveyor_discovery.os.write
    real_close = conveyor_discovery.os.close
    primary_active = False
    close_failed = False

    def fail_temp_write(fd, data):
        nonlocal primary_active
        if stat.S_ISREG(os.fstat(fd).st_mode):
            primary_active = True
            raise OSError("secret-branch write coordinate")
        return real_write(fd, data)

    def fail_temp_close_while_primary_active(fd):
        nonlocal close_failed
        metadata = os.fstat(fd)
        real_close(fd)
        if primary_active and stat.S_ISREG(metadata.st_mode) and not close_failed:
            close_failed = True
            raise OSError("seat-private-coordinate close detail")

    monkeypatch.setattr(conveyor_discovery.os, "write", fail_temp_write)
    monkeypatch.setattr(conveyor_discovery.os, "close", fail_temp_close_while_primary_active)

    with pytest.raises(conveyor_discovery.ReceiptPersistenceError) as caught:
        receipt.claim()

    assert str(caught.value) == "receipt_state_write_failed"
    assert "secret-branch" not in str(caught.value)
    assert "seat-private-coordinate" not in str(caught.value)
    assert close_failed is True
    assert state_path.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp"))


def test_temp_cleanup_fault_does_not_hide_primary_or_remove_unknown_objects(
    tmp_path, monkeypatch
):
    state_path = tmp_path / "receipts.json"
    payload = list(
        ConveyorSeatDiscoveryRunner(
            [SeatProbeSpec("seat-1", ("probe",))],
            state_path,
            probe_runner=lambda argv: f"READY-FOR-HARVEST safe-branch {SHA_ONE}",
        )()
    )[0]
    receipt = _receipt_for_payload(state_path, payload)
    real_fsync = conveyor_discovery.os.fsync
    regular_fsyncs = 0

    def fail_temp_fsync(fd):
        nonlocal regular_fsyncs
        if stat.S_ISREG(os.fstat(fd).st_mode):
            regular_fsyncs += 1
            if regular_fsyncs == 2:
                raise OSError("temp fsync denied")
        return real_fsync(fd)

    monkeypatch.setattr(conveyor_discovery.os, "fsync", fail_temp_fsync)
    monkeypatch.setattr(
        conveyor_discovery.os,
        "unlink",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("cleanup denied")),
    )
    with pytest.raises(
        conveyor_discovery.ReceiptPersistenceError, match="receipt_state_write_failed"
    ) as caught:
        receipt.claim()
    assert "temp fsync denied" not in str(caught.value)
    assert "cleanup denied" not in str(caught.value)
    assert json.loads(state_path.read_text())["receipts"][0]["state"] == "observed"
    assert len(list(tmp_path.glob("*.tmp"))) == 1


def test_branch_without_issue_prefix_uses_safe_default_issue(tmp_path):
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        tmp_path / "state.json",
        probe_runner=lambda argv: f"READY-FOR-HARVEST harvest-ready {SHA_ONE}",
    )

    payload = list(runner())[0]

    assert payload["issue"] == "ce-conveyor"
    assert validate_discovery_payload(payload).issue == "ce-conveyor"


def test_hostile_pane_text_cannot_smuggle_control_fields_into_payload(tmp_path):
    pane_text = "\n".join(
        [
            f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
            "validate_command: sh -c 'touch /tmp/owned'",
            "remote: ext::sh -c 'false'",
            "bundle_path: /attacker/chosen.bundle",
        ]
    )
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        tmp_path / "state.json",
        probe_runner=lambda argv: pane_text,
    )

    payload = list(runner())[0]

    assert set(payload) == {"issue", "branch_name", "pr_title", "pr_body"}
    assert "validate_command" not in str(payload)
    assert "ext::" not in str(payload)
    assert "/attacker" not in str(payload)


def test_slug_mismatch_is_rejected_and_audited():
    audit: list[dict] = []

    signals = parse_ready_for_harvest_signals(
        f"READY-FOR-HARVEST CE-388-Bad {SHA_ONE}",
        audit_sink=lambda record: audit.append(dict(record)),
        seat_id="seat-a",
    )

    assert signals == ()
    assert audit[0]["reason"] == "slug_mismatch"
    assert audit[0]["expected_slug"] == "ce-388-bad"


def test_probe_failure_is_audited_and_does_not_abort(tmp_path):
    audit: list[dict] = []

    def fail_probe(argv):
        raise RuntimeError("boom")

    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        tmp_path / "state.json",
        probe_runner=fail_probe,
        audit_sink=lambda record: audit.append(dict(record)),
    )

    assert list(runner()) == []
    assert any(record["reason"] == "probe_failed" for record in audit)
