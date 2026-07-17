from __future__ import annotations

import json
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
    state_path.write_text("{not json", encoding="utf-8")
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

    with pytest.raises(ValueError, match="receipt_state_lock_unavailable:PermissionError"):
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

    def fail_replace(*_args):
        raise OSError("replace denied")

    monkeypatch.setattr(conveyor_discovery.os, "replace", fail_replace)

    with pytest.raises(ValueError, match="receipt_state_write_failed:OSError"):
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
    events: list[str] = []
    parent_fd: int | None = None
    real_replace = conveyor_discovery.os.replace
    real_open = conveyor_discovery.os.open
    real_fsync = conveyor_discovery.os.fsync
    real_close = conveyor_discovery.os.close

    def record_replace(source, target):
        events.append("replace")
        return real_replace(source, target)

    def record_open(path, flags, *args):
        nonlocal parent_fd
        fd = real_open(path, flags, *args)
        if Path(path) == state_path.parent:
            parent_fd = fd
            events.append("parent-open")
        return fd

    def record_fsync(fd):
        if fd == parent_fd:
            events.append("parent-fsync")
        return real_fsync(fd)

    def record_close(fd):
        if fd == parent_fd:
            events.append("parent-close")
        return real_close(fd)

    monkeypatch.setattr(conveyor_discovery.os, "replace", record_replace)
    monkeypatch.setattr(conveyor_discovery.os, "open", record_open)
    monkeypatch.setattr(conveyor_discovery.os, "fsync", record_fsync)
    monkeypatch.setattr(conveyor_discovery.os, "close", record_close)

    conveyor_discovery._write_receipt_state(state_path, [])

    assert events == ["replace", "parent-open", "parent-fsync", "parent-close"]


def test_receipt_parent_fsync_failure_refuses_write_and_cleans_temp(tmp_path, monkeypatch):
    state_path = tmp_path / "receipts.json"
    real_open = conveyor_discovery.os.open
    real_fsync = conveyor_discovery.os.fsync
    parent_fd: int | None = None

    def record_open(path, flags, *args):
        nonlocal parent_fd
        fd = real_open(path, flags, *args)
        if Path(path) == state_path.parent:
            parent_fd = fd
        return fd

    def fail_parent_fsync(fd):
        if fd == parent_fd:
            raise OSError("directory fsync denied")
        return real_fsync(fd)

    monkeypatch.setattr(conveyor_discovery.os, "open", record_open)
    monkeypatch.setattr(conveyor_discovery.os, "fsync", fail_parent_fsync)

    with pytest.raises(ValueError, match="receipt_state_write_failed:OSError"):
        conveyor_discovery._write_receipt_state(state_path, [])

    assert not list(tmp_path.glob("*.tmp"))


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
