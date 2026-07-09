from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence

import pytest

from creator_engine_validator.conveyor_discovery import SeatProbeSpec
from creator_engine_validator.seat_watch_daemon import SeatWatchDaemon
from creator_engine_validator.seat_watch_runner import ConfigError, load_config

SHA = "a" * 40


def _spec(seat_id: str = "seat-a") -> SeatProbeSpec:
    return SeatProbeSpec(seat_id=seat_id, argv=("probe", seat_id))


def _daemon(
    outputs: Sequence[str],
    *,
    idle_threshold_polls: int = 5,
    dispatch_patterns: Sequence[str] = (),
) -> SeatWatchDaemon:
    calls = {"count": 0}

    def probe_runner(_argv: Sequence[str]) -> str:
        index = min(calls["count"], len(outputs) - 1)
        calls["count"] += 1
        return outputs[index]

    return SeatWatchDaemon(
        [_spec()],
        idle_threshold_polls=idle_threshold_polls,
        dispatch_patterns=dispatch_patterns,
        probe_runner=probe_runner,
        now=lambda: "2026-07-09T06:30:00Z",
    )


def _base_env(tmp_path) -> dict[str, str]:
    return {
        "CE_SEAT_WATCH_SEAT_PROBES": json.dumps(
            [{"seat_id": "seat-a", "argv": ["probe", "seat-a"]}]
        ),
        "CE_SEAT_WATCH_FEED_PATH": str(tmp_path / "seat-watch.jsonl"),
        "CE_DAEMON_LEASE_ROOT": str(tmp_path / "leases"),
    }


def test_ready_signal_emitted():
    daemon = _daemon([f"READY-FOR-HARVEST ce-p5-seatwatch-s1 {SHA}"])

    events = daemon.run_once(0)

    assert len(events) == 1
    event = events[0]
    assert event.event_type == "ready_signal"
    assert event.detail["branch"] == "ce-p5-seatwatch-s1"
    assert event.detail["sha"] == SHA


def test_blocked_signal_emitted():
    daemon = _daemon(["BLOCKED ce-p5-seatwatch-s1 territory-collision: unexpected file"])

    events = daemon.run_once(0)

    assert len(events) == 1
    event = events[0]
    assert event.event_type == "blocked_signal"
    assert event.detail["branch"] == "ce-p5-seatwatch-s1"
    assert event.detail["reason"] == "territory-collision: unexpected file"


def test_idle_without_signal_emitted():
    daemon = _daemon(["waiting"], idle_threshold_polls=5)

    events = [event for poll in range(5) for event in daemon.run_once(poll)]

    assert [event.event_type for event in events] == ["idle_without_signal"]
    assert events[0].poll_index == 4
    assert events[0].detail["polls_unchanged"] == 5


def test_idle_resets_on_text_change():
    daemon = _daemon(["same", "same", "same", "same", "different"], idle_threshold_polls=5)

    events = [event for poll in range(5) for event in daemon.run_once(poll)]

    assert [event for event in events if event.event_type == "idle_without_signal"] == []


def test_idle_resets_after_emission():
    daemon = _daemon(["same"], idle_threshold_polls=3)

    events = [event for poll in range(6) for event in daemon.run_once(poll)]

    idle_events = [event for event in events if event.event_type == "idle_without_signal"]
    assert [event.poll_index for event in idle_events] == [2, 5]


def test_pane_error_exit_143():
    def probe_runner(_argv: Sequence[str]) -> str:
        raise subprocess.CalledProcessError(143, ["herdr", "pane", "read", "w1:p1"])

    daemon = SeatWatchDaemon([_spec()], probe_runner=probe_runner, now=lambda: "now")

    events = daemon.run_once(0)

    assert events[0].event_type == "pane_error"
    assert events[0].detail["error_class"] == "exit_143"


def test_pane_error_auth():
    def probe_runner(_argv: Sequence[str]) -> str:
        raise RuntimeError("unauthorized: token invalid")

    daemon = SeatWatchDaemon([_spec()], probe_runner=probe_runner, now=lambda: "now")

    events = daemon.run_once(0)

    assert events[0].event_type == "pane_error"
    assert events[0].detail["error_class"] == "auth"


def test_pane_error_limit():
    def probe_runner(_argv: Sequence[str]) -> str:
        raise RuntimeError("rate limit exceeded (429)")

    daemon = SeatWatchDaemon([_spec()], probe_runner=probe_runner, now=lambda: "now")

    events = daemon.run_once(0)

    assert events[0].event_type == "pane_error"
    assert events[0].detail["error_class"] == "limit"


def test_pane_error_probe_failed():
    def probe_runner(_argv: Sequence[str]) -> str:
        raise subprocess.CalledProcessError(1, ["herdr", "pane", "read", "w1:p1"])

    daemon = SeatWatchDaemon([_spec()], probe_runner=probe_runner, now=lambda: "now")

    events = daemon.run_once(0)

    assert events[0].event_type == "pane_error"
    assert events[0].detail["error_class"] == "probe_failed"


def test_pane_error_unknown():
    def probe_runner(_argv: Sequence[str]) -> str:
        raise ValueError("something unexpected")

    daemon = SeatWatchDaemon([_spec()], probe_runner=probe_runner, now=lambda: "now")

    events = daemon.run_once(0)

    assert events[0].event_type == "pane_error"
    assert events[0].detail["error_class"] == "unknown"


def test_dispatch_delivery_ack_emitted():
    daemon = _daemon(
        ["nothing yet", "received DISPATCH POINTER abc.md"],
        dispatch_patterns=["DISPATCH POINTER"],
    )

    first = daemon.run_once(0)
    second = daemon.run_once(1)

    assert first == []
    assert [event.event_type for event in second] == ["dispatch_delivery_ack"]
    assert second[0].detail["pattern_matched"] == "DISPATCH POINTER"


def test_dispatch_no_duplicate_ack():
    daemon = _daemon(
        [
            "nothing yet",
            "received DISPATCH POINTER abc.md",
            "received DISPATCH POINTER abc.md",
            "received DISPATCH POINTER abc.md",
        ],
        dispatch_patterns=["DISPATCH POINTER"],
    )

    events = [event for poll in range(4) for event in daemon.run_once(poll)]

    assert [event.event_type for event in events] == ["dispatch_delivery_ack"]


def test_dispatch_ack_case_insensitive():
    daemon = _daemon(
        ["nothing yet", "received DISPATCH POINTER abc.md"],
        dispatch_patterns=["dispatch pointer"],
    )

    daemon.run_once(0)
    events = daemon.run_once(1)

    assert [event.event_type for event in events] == ["dispatch_delivery_ack"]


def test_config_load_happy_path(tmp_path):
    env = _base_env(tmp_path)
    env.update(
        {
            "CE_SEAT_WATCH_INTERVAL_SECONDS": "12.5",
            "CE_SEAT_WATCH_IDLE_THRESHOLD_POLLS": "7",
            "CE_SEAT_WATCH_DISPATCH_PATTERNS": json.dumps(["one", "two"]),
            "CE_SEAT_WATCH_WEBHOOK_FILE": str(tmp_path / "webhook.jsonl"),
            "CE_SEAT_WATCH_ITERATIONS": "3",
            "CE_DAEMON_LEASE_TTL_SECONDS": "90",
            "CE_DAEMON_HOLDER_ID": "holder",
        }
    )

    config = load_config(env)

    assert len(config.seat_probes) == 1
    assert config.seat_probes[0].seat_id == "seat-a"
    assert config.seat_probes[0].argv == ("probe", "seat-a")
    assert config.interval_seconds == 12.5
    assert config.idle_threshold_polls == 7
    assert config.dispatch_patterns == ("one", "two")
    assert config.iterations == 3
    assert config.holder_id == "holder"


def test_config_missing_required(tmp_path):
    env = _base_env(tmp_path)
    del env["CE_SEAT_WATCH_SEAT_PROBES"]

    with pytest.raises(ConfigError):
        load_config(env)


def test_config_bad_json_probes(tmp_path):
    env = _base_env(tmp_path)
    env["CE_SEAT_WATCH_SEAT_PROBES"] = "not-json"

    with pytest.raises(ConfigError):
        load_config(env)


def test_config_missing_feed_path(tmp_path):
    env = _base_env(tmp_path)
    del env["CE_SEAT_WATCH_FEED_PATH"]

    with pytest.raises(ConfigError):
        load_config(env)


def test_config_invalid_interval(tmp_path):
    env = _base_env(tmp_path)
    env["CE_SEAT_WATCH_INTERVAL_SECONDS"] = "0"

    with pytest.raises(ConfigError):
        load_config(env)


def test_config_invalid_idle_threshold(tmp_path):
    env = _base_env(tmp_path)
    env["CE_SEAT_WATCH_IDLE_THRESHOLD_POLLS"] = "0"

    with pytest.raises(ConfigError):
        load_config(env)


def test_multiple_seats():
    specs = [_spec("seat-A"), _spec("seat-B")]

    def probe_runner(argv: Sequence[str]) -> str:
        seat_id = argv[1]
        if seat_id == "seat-A":
            return f"READY-FOR-HARVEST ce-p5-seatwatch-s1 {SHA}"
        return "unchanged text"

    daemon = SeatWatchDaemon(specs, probe_runner=probe_runner, now=lambda: "now")

    events = daemon.run_once(0)

    assert [(event.seat_id, event.event_type) for event in events] == [
        ("seat-A", "ready_signal")
    ]
    assert daemon.run_once(1)[0].seat_id == "seat-A"
