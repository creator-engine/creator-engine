from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from creator_engine_validator import seat_lifecycle


def _register(tmp_path: Path, *, exit_code: int) -> Path:
    events = tmp_path / ".ce" / "state" / "dispatches" / "seat-x" / "events.jsonl"
    events.parent.mkdir(parents=True)
    events.write_text(
        "\n".join(
            [
                json.dumps({"event": "launched", "seat_id": "seat-x"}),
                json.dumps({"event": "exited", "seat_id": "seat-x", "exit_code": exit_code}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    result = seat_lifecycle.register_spawn(
        ledger_root=tmp_path / ".ce" / "state" / "active-work-ledger",
        repo_root=tmp_path,
        seat_id="seat-x",
        owner_controller_id="controller",
        host_id="host-a",
        launch_surface="ce_launch",
        terminal={"kind": "tmux", "pane_pid": 123},
        harness_kind="codex",
        events_ref=str(events),
    )
    return result.record_path


def test_reconcile_from_sentinel_exit_127_marks_dead(tmp_path):
    record_path = _register(tmp_path, exit_code=127)
    reconciled = seat_lifecycle.reconcile_from_sentinel_events(
        record_path,
        now=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
    )

    assert reconciled is True
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    assert record["lifecycle"]["state"] == "dead"
    assert record["lifecycle"]["state_reason"] == "sentinel-exited-nonzero"
    assert record["lifecycle"]["terminal_exit_code"] == 127
    assert record["lifecycle"]["state_since"] == "2026-06-23T12:00:00Z"
    assert record["lifecycle"]["last_activity_at"] == "2026-06-23T12:00:00Z"


def test_reconcile_from_sentinel_exit_zero_marks_spent_and_is_idempotent(tmp_path):
    record_path = _register(tmp_path, exit_code=0)
    first = seat_lifecycle.reconcile_from_sentinel_events(
        record_path,
        now=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
    )
    before = record_path.read_text(encoding="utf-8")
    second = seat_lifecycle.reconcile_from_sentinel_events(
        record_path,
        now=datetime(2026, 6, 23, 12, 5, tzinfo=UTC),
    )

    record = yaml.safe_load(before)
    assert first is True
    assert second is False
    assert record_path.read_text(encoding="utf-8") == before
    assert record["lifecycle"]["state"] == "spent"
    assert record["lifecycle"]["state_reason"] == "sentinel-exited-zero"
    assert record["lifecycle"]["terminal_exit_code"] == 0


def test_register_spawn_preserves_herdr_terminal_identity(tmp_path):
    events = tmp_path / ".ce" / "state" / "dispatches" / "seat-herdr" / "events.jsonl"
    events.parent.mkdir(parents=True)
    events.write_text(
        json.dumps({"event": "launched", "seat_id": "seat-herdr"}) + "\n",
        encoding="utf-8",
    )
    result = seat_lifecycle.register_spawn(
        ledger_root=tmp_path / ".ce" / "state" / "active-work-ledger",
        repo_root=tmp_path,
        seat_id="seat-herdr",
        owner_controller_id="controller",
        host_id="host-a",
        launch_surface="ce_lane_launch",
        terminal={
            "kind": "herdr",
            "surface_ref": "herdr-surface-918aa1506d296ee1a72da70227854392",
            "pane_id": "pane-1",
            "pid": 4242,
        },
        harness_kind="codex",
        events_ref=str(events),
    )
    record = yaml.safe_load(result.record_path.read_text(encoding="utf-8"))
    assert record["terminal"] == {
        "kind": "herdr",
        "surface_ref": "herdr-surface-918aa1506d296ee1a72da70227854392",
        "pane_id": "pane-1",
        "pid": 4242,
        "attached_controller": {"attached": False, "evidence": "not-sampled"},
    }
    assert "/run/ce/herdr/control.sock" not in repr(record["terminal"])
