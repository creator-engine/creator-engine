"""Tests for the shared daemon heartbeat contract and passive emitter."""

from __future__ import annotations

import json
import stat
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from creator_engine_validator import daemon_heartbeat as heartbeat


NOW = datetime(2026, 7, 11, 12, 34, 56, tzinfo=timezone.utc)


def _record() -> dict[str, object]:
    return {
        "schema_version": 1,
        "daemon_id": "queue-daemon",
        "pass_index": 42,
        "ts": "2026-07-11T12:34:56Z",
        "status": "running",
        "expected_interval_seconds": 30,
        "unit": "ce-queue-daemon.service",
        "scope": "system",
    }


def _emitter(tmp_path, **overrides):
    kwargs = {
        "daemon_id": "queue-daemon",
        "expected_interval_seconds": 30,
        "unit": "ce-queue-daemon.service",
        "scope": "system",
        "clock": lambda: NOW,
    }
    kwargs.update(overrides)
    return heartbeat.DaemonHeartbeatEmitter(tmp_path / "heartbeat.json", **kwargs)


def test_schema_accepts_complete_non_secret_record() -> None:
    assert heartbeat.validate_heartbeat(_record()) == _record()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("daemon_id", "INVALID/daemon"),
        ("pass_index", -1),
        ("ts", "not-a-date"),
        ("ts", "2026-07-11T12:34:56+01:00"),
        ("status", "healthy"),
        ("expected_interval_seconds", 0),
        ("unit", "../../secret.service"),
        ("scope", "global"),
    ],
)
def test_schema_rejects_malformed_fields(field: str, value: object) -> None:
    record = _record()
    record[field] = value
    with pytest.raises(heartbeat.DaemonHeartbeatError):
        heartbeat.validate_heartbeat(record)


@pytest.mark.parametrize("secret_field", ["token", "password", "credential", "private_key"])
def test_schema_rejects_unknown_secret_bearing_fields(secret_field: str) -> None:
    record = _record()
    record[secret_field] = "must-not-persist"
    with pytest.raises(heartbeat.DaemonHeartbeatError):
        heartbeat.validate_heartbeat(record)


def test_emit_round_trip_is_atomic_mode_0600_and_deterministic(tmp_path) -> None:
    emitter = _emitter(tmp_path)
    emitted = emitter.emit("starting", 0)

    assert emitted["ts"] == "2026-07-11T12:34:56.000000Z"
    assert heartbeat.read_heartbeat(tmp_path / "heartbeat.json") == emitted
    assert stat.S_IMODE((tmp_path / "heartbeat.json").stat().st_mode) == 0o600
    assert not list(tmp_path.glob(".heartbeat.json.*.tmp"))


def test_atomic_replace_failure_preserves_previous_record(tmp_path, monkeypatch) -> None:
    emitter = _emitter(tmp_path)
    original = emitter.emit("starting", 0)

    def fail_replace(_source, _target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(heartbeat.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        emitter.emit("running", 1, now=NOW + timedelta(seconds=30))

    assert heartbeat.read_heartbeat(tmp_path / "heartbeat.json") == original
    assert not list(tmp_path.glob(".heartbeat.json.*.tmp"))


def test_structured_journal_sink_receives_stable_non_secret_payload(tmp_path) -> None:
    journal = []
    emitter = _emitter(tmp_path, journal_sink=journal.append)
    emitted = emitter.emit("running", 1)

    assert journal == [
        {
            "CE_EVENT": "daemon_heartbeat",
            "CE_DAEMON_ID": "queue-daemon",
            **emitted,
        }
    ]
    serialized = json.dumps(journal)
    assert all(marker not in serialized for marker in ("token", "password", "credential", "private_key"))


def test_periodic_running_seam_never_sleeps_or_starts_threads(tmp_path) -> None:
    emitter = _emitter(tmp_path)
    emitter.emit("starting", 0)

    assert emitter.emit_periodic_running(1, now=NOW + timedelta(seconds=29)) is None
    periodic = emitter.emit_periodic_running(1, now=NOW + timedelta(seconds=30))

    assert periodic is not None
    assert periodic["status"] == "running"
    assert periodic["pass_index"] == 1


def test_naive_injected_clock_is_rejected_before_write(tmp_path) -> None:
    emitter = _emitter(tmp_path, clock=lambda: datetime(2026, 7, 11, 12, 34, 56))
    with pytest.raises(heartbeat.DaemonHeartbeatError, match="timezone-aware"):
        emitter.emit("starting", 0)
    assert not (tmp_path / "heartbeat.json").exists()


def test_pass_index_cannot_move_backwards_even_after_reopen(tmp_path) -> None:
    _emitter(tmp_path).emit("pass_complete", 3)
    reopened = _emitter(tmp_path)

    with pytest.raises(heartbeat.DaemonHeartbeatError, match="monotonic"):
        reopened.emit("running", 2, now=NOW + timedelta(seconds=30))


def test_existing_identity_mismatch_is_refused_before_replace(tmp_path) -> None:
    original = _emitter(tmp_path).emit("running", 1)
    with pytest.raises(heartbeat.DaemonHeartbeatError, match="daemon_id"):
        _emitter(tmp_path, daemon_id="review-pickup")
    assert heartbeat.read_heartbeat(tmp_path / "heartbeat.json") == original


def test_read_rejects_non_object_and_malformed_json(tmp_path) -> None:
    path = tmp_path / "heartbeat.json"
    for content in ("[]\n", "{broken\n"):
        path.write_text(content, encoding="utf-8")
        with pytest.raises(heartbeat.DaemonHeartbeatError):
            heartbeat.read_heartbeat(path)


def test_validation_does_not_mutate_caller_record() -> None:
    record = _record()
    before = deepcopy(record)
    heartbeat.validate_heartbeat(record)
    assert record == before
