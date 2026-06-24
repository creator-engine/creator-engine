from __future__ import annotations

import json
from pathlib import Path

import yaml

from creator_engine_validator import v3_cli
from creator_engine_validator.forge import seats_status


def _event(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def _lifecycle(
    path: Path,
    *,
    seat_id: str,
    state: str,
    events_ref: Path | None = None,
    branch: str | None = None,
    ticket: str | None = None,
    run_id: str | None = None,
) -> None:
    record = {
        "kind": "seat-lifecycle-record",
        "record_type": "seat_lifecycle",
        "schema_version": "1",
        "seat": {"seat_id": seat_id, "host_id": "host-a"},
        "work": {},
        "dispatch": {},
        "lifecycle": {"state": state},
    }
    if branch:
        record["work"]["branch"] = branch
    if ticket:
        record["work"]["ticket"] = ticket
    if run_id:
        record["dispatch"]["run_id"] = run_id
    if events_ref:
        record["dispatch"]["events_ref"] = str(events_ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")


def test_discover_seats_from_lifecycle_records_and_sentinels(tmp_path):
    state_root = tmp_path / ".ce" / "state"
    ledger = state_root / "active-work-ledger"
    sentinel = state_root / "dispatches" / "seat-sentinel" / "events.jsonl"
    _event(sentinel, {"event": "launched", "seat_id": "seat-sentinel"})
    _lifecycle(
        ledger / "seats" / "host-a" / "seat-record.yaml",
        seat_id="seat-record",
        state="alive",
    )

    refs = seats_status.discover_seats(state_root)

    assert [ref.seat_id for ref in refs] == ["seat-sentinel", "seat-record"]
    assert any(ref.events_path == sentinel for ref in refs)
    assert any(ref.lifecycle_path and ref.lifecycle_path.name == "seat-record.yaml" for ref in refs)


def test_discover_dedupes_absolute_lifecycle_event_ref_with_relative_root(tmp_path, monkeypatch):
    state_root = tmp_path / ".ce" / "state"
    ledger = state_root / "active-work-ledger"
    sentinel = state_root / "dispatches" / "seat-a" / "events.jsonl"
    _event(sentinel, {"event": "launched", "seat_id": "seat-a"})
    _lifecycle(
        ledger / "seats" / "host-a" / "seat-a.yaml",
        seat_id="seat-a",
        state="alive",
        events_ref=sentinel.resolve(),
    )
    monkeypatch.chdir(tmp_path)

    refs = seats_status.discover_seats(Path(".ce/state"))

    assert [ref.seat_id for ref in refs] == ["seat-a"]
    assert refs[0].lifecycle_path is not None


def test_classifies_up_idle_and_working(tmp_path):
    state_root = tmp_path / ".ce" / "state"
    ledger = state_root / "active-work-ledger"
    up_events = state_root / "dispatches" / "seat-up" / "events.jsonl"
    _event(up_events, {"event": "launched", "seat_id": "seat-up", "run_id": None})
    _lifecycle(ledger / "seats" / "host-a" / "seat-idle.yaml", seat_id="seat-idle", state="idle")
    _lifecycle(
        ledger / "seats" / "host-a" / "seat-working.yaml",
        seat_id="seat-working",
        state="alive",
        branch="ce95-seats-ls",
        ticket="creator-engine#95",
    )

    statuses = {
        status.seat_id: status
        for status in seats_status.read_seat_states(seats_status.discover_seats(state_root))
    }

    assert statuses["seat-up"].state == seats_status.STATE_UP
    assert statuses["seat-idle"].state == seats_status.STATE_IDLE
    assert statuses["seat-working"].state == seats_status.STATE_WORKING
    assert statuses["seat-working"].branch == "ce95-seats-ls"
    assert statuses["seat-working"].lane == "creator-engine#95"


def test_missing_state_fails_safe_as_unknown(tmp_path):
    missing_events = tmp_path / ".ce" / "state" / "dispatches" / "missing-seat" / "events.jsonl"
    ref = seats_status.SeatRef(seat_id="missing-seat", events_path=missing_events)

    status = seats_status.read_seat_state(ref)

    assert status.state == seats_status.STATE_UNKNOWN
    assert status.source == "missing-state"
    assert status.reason == "missing-events"


def test_v3_cli_seats_ls_outputs_table(tmp_path, capsys):
    state_root = tmp_path / ".ce" / "state"
    events = state_root / "dispatches" / "seat-cli" / "events.jsonl"
    _event(events, {"event": "launched", "seat_id": "seat-cli", "run_id": "run-1"})

    ret = v3_cli.main(["seats", "ls", "--root", str(state_root)])

    assert ret == 0
    out = capsys.readouterr().out
    assert "SEAT" in out
    assert "seat-cli" in out
    assert seats_status.STATE_WORKING in out
