from __future__ import annotations

import json

import pytest

from creator_engine_validator.conveyor_daemon import ConveyorDaemonItem
from creator_engine_validator.conveyor_discovery import (
    ConveyorSeatDiscoveryRunner,
    ReadyForHarvestSignal,
    SeatProbeSpec,
    parse_ready_for_harvest_signals,
)
from creator_engine_validator.pickup_payload_schema import validate_discovery_payload

SHA_ONE = "a" * 40
SHA_TWO = "b" * 40
SHA_THREE = "c" * 40


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


def test_runner_dedupes_across_runs_and_writes_atomic_state(tmp_path):
    state_path = tmp_path / "processed.json"
    spec = SeatProbeSpec("seat-1", ("probe", "seat-1"))
    pane_text = f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}"

    runner = ConveyorSeatDiscoveryRunner(
        [spec],
        state_path,
        probe_runner=lambda argv: pane_text,
    )

    first = list(runner())
    second = list(runner())

    assert len(first) == 1
    assert second == []
    assert first[0]["branch_name"] == "ce-388-conveyor-discovery"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state == {
        "processed": [
            {
                "seat_id": "seat-1",
                "branch": "ce-388-conveyor-discovery",
                "sha": SHA_ONE,
            }
        ]
    }
    assert not list(tmp_path.glob("*.tmp"))


def test_corrupt_state_recovers_and_is_rewritten(tmp_path):
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

    assert len(payloads) == 1
    assert any(record["reason"] == "corrupt_state" for record in audit)
    assert json.loads(state_path.read_text(encoding="utf-8"))["processed"][0]["sha"] == SHA_ONE


def test_emitted_payload_passes_schema_and_daemon_mapping(tmp_path):
    runner = ConveyorSeatDiscoveryRunner(
        [SeatProbeSpec("seat-1", ("probe",))],
        tmp_path / "state.json",
        probe_runner=lambda argv: f"READY-FOR-HARVEST ce-388-conveyor-discovery {SHA_ONE}",
    )

    payload = list(runner())[0]

    assert set(payload) == {"issue", "branch_name", "pr_title", "pr_body"}
    assert validate_discovery_payload(payload).to_dict() == payload
    item = ConveyorDaemonItem.from_mapping(payload)
    assert item.branch == "ce-388-conveyor-discovery"
    assert item.issue == "388"
    assert SHA_ONE in payload["pr_body"]


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
