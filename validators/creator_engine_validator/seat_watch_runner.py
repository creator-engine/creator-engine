"""Environment loader and entrypoint for the observe-only seat-watch daemon."""

from __future__ import annotations

import json
import os
import signal
import socket
import sys
import tempfile
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .conveyor_discovery import SeatProbeSpec
from .daemon_lease import (
    DEFAULT_LEASE_TTL_SECONDS,
    DaemonLease,
    DaemonLeaseError,
    acquire,
)
from .seat_watch_daemon import SeatWatchDaemon, WatchEvent

DEFAULT_INTERVAL_SECONDS = 30.0
DEFAULT_IDLE_THRESHOLD_POLLS = 5
EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIG = 2
EXIT_LEASE_UNAVAILABLE = 73
DETECTOR_EVENT_TYPES = {
    "idle_without_signal": "idle-without-signal",
    "dispatch_undelivered": "dispatch-undelivered",
}


class ConfigError(ValueError):
    """The seat-watch daemon environment is incomplete or malformed."""


@dataclass(frozen=True)
class SeatWatchConfig:
    seat_probes: tuple[SeatProbeSpec, ...]
    feed_path: Path
    state_root: Path
    lease_root: Path
    detector_events_path: Path
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS
    idle_threshold_polls: int = DEFAULT_IDLE_THRESHOLD_POLLS
    dispatch_patterns: tuple[str, ...] = ()
    webhook_file: Path | None = None
    iterations: int | None = None
    lease_ttl_seconds: float = DEFAULT_LEASE_TTL_SECONDS
    holder_id: str | None = None


def load_config(env: Mapping[str, str] | None = None) -> SeatWatchConfig:
    source = os.environ if env is None else env
    state_root = Path(
        source.get("CE_DAEMON_STATE_ROOT") or _require_env(source, "CE_DAEMON_LEASE_ROOT")
    )
    return SeatWatchConfig(
        seat_probes=_parse_seat_probes(_require_env(source, "CE_SEAT_WATCH_SEAT_PROBES")),
        feed_path=_required_absolute_path(source, "CE_SEAT_WATCH_FEED_PATH"),
        state_root=state_root,
        lease_root=Path(_require_env(source, "CE_DAEMON_LEASE_ROOT")),
        detector_events_path=state_root / "seat-watch" / "detector-events.jsonl",
        interval_seconds=_parse_positive_float(
            source,
            "CE_SEAT_WATCH_INTERVAL_SECONDS",
            DEFAULT_INTERVAL_SECONDS,
        ),
        idle_threshold_polls=_parse_positive_int(
            source,
            "CE_SEAT_WATCH_IDLE_THRESHOLD_POLLS",
            DEFAULT_IDLE_THRESHOLD_POLLS,
        ),
        dispatch_patterns=_parse_dispatch_patterns(
            source.get("CE_SEAT_WATCH_DISPATCH_PATTERNS")
        ),
        webhook_file=_optional_absolute_path(source, "CE_SEAT_WATCH_WEBHOOK_FILE"),
        iterations=_parse_iterations(source),
        lease_ttl_seconds=_parse_positive_float(
            source,
            "CE_DAEMON_LEASE_TTL_SECONDS",
            DEFAULT_LEASE_TTL_SECONDS,
        ),
        holder_id=source.get("CE_DAEMON_HOLDER_ID") or None,
    )


def main_with_existing_lease(
    lease: DaemonLease,
    env: Mapping[str, str] | None = None,
) -> int:
    try:
        config = load_config(env)
    except ConfigError as exc:
        _error(str(exc))
        lease.release()
        return EXIT_CONFIG
    return _run_loop(config, lease)


def main(env: Mapping[str, str] | None = None) -> int:
    try:
        config = load_config(env)
    except ConfigError as exc:
        _error(str(exc))
        return EXIT_CONFIG

    _ensure_private_dir(config.state_root)
    _ensure_private_dir(config.lease_root)
    _ensure_private_dir(config.feed_path.parent)
    _ensure_private_dir(config.detector_events_path.parent)
    if config.webhook_file is not None:
        _ensure_private_dir(config.webhook_file.parent)
    try:
        lease = acquire(
            "seat-watch",
            _holder_id(config),
            state_root=config.lease_root,
            ttl_seconds=config.lease_ttl_seconds,
        )
    except DaemonLeaseError as exc:
        _error(_lease_refusal_error(config, exc))
        return EXIT_LEASE_UNAVAILABLE
    return _run_loop(config, lease)


def _run_loop(config: SeatWatchConfig, lease: DaemonLease) -> int:
    stop_event = threading.Event()
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    previous_sigint = signal.getsignal(signal.SIGINT)

    def _request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    try:
        daemon = SeatWatchDaemon(
            config.seat_probes,
            idle_threshold_polls=config.idle_threshold_polls,
            dispatch_patterns=config.dispatch_patterns,
        )
        poll_index = 0
        while not stop_event.is_set():
            events = daemon.run_once(poll_index)
            for event in events:
                _write_event(config.feed_path, event)
                _write_detector_record(config.detector_events_path, event)
                if config.webhook_file is not None:
                    _write_event(config.webhook_file, event)
            poll_index += 1
            if config.iterations is not None and poll_index >= config.iterations:
                break
            stop_event.wait(config.interval_seconds)
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        signal.signal(signal.SIGINT, previous_sigint)
        lease.release()
    return EXIT_OK


def _write_event(path: Path, event: WatchEvent) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    line = json.dumps(event.as_dict(), sort_keys=True, default=str) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".seat-watch-event.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def _write_detector_record(path: Path, event: WatchEvent) -> None:
    detector_class = DETECTOR_EVENT_TYPES.get(event.event_type)
    if detector_class is None:
        return
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    record = {
        "schema_version": event.schema_version,
        "seat_id": event.seat_id,
        "class": detector_class,
        "timestamp": event.ts,
        "evidence": {
            "poll_index": event.poll_index,
            **event.detail,
        },
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _holder_id(config: SeatWatchConfig) -> str:
    return config.holder_id or f"seat-watch:{socket.gethostname()}:{os.getpid()}"


def _lease_refusal_error(config: SeatWatchConfig, exc: DaemonLeaseError) -> str:
    return (
        "seat-watch singleton lease refused: "
        f"{exc}; lease_path={config.lease_root / 'seat-watch.lease'}"
    )


def _error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)


def _require_env(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if value is None or not value.strip():
        raise ConfigError(f"missing required environment variable: {name}")
    return value


def _required_absolute_path(env: Mapping[str, str], name: str) -> Path:
    path = Path(_require_env(env, name))
    if not path.is_absolute():
        raise ConfigError(f"{name} must be an absolute path")
    return path


def _optional_absolute_path(env: Mapping[str, str], name: str) -> Path | None:
    value = env.get(name)
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        raise ConfigError(f"{name} must be an absolute path")
    return path


def _parse_positive_float(
    env: Mapping[str, str],
    name: str,
    default: float,
) -> float:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be numeric") from exc
    if value <= 0:
        raise ConfigError(f"{name} must be positive")
    return value


def _parse_positive_int(
    env: Mapping[str, str],
    name: str,
    default: int,
) -> int:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if value < 1:
        raise ConfigError(f"{name} must be >= 1")
    return value


def _parse_iterations(env: Mapping[str, str]) -> int | None:
    raw = env.get("CE_SEAT_WATCH_ITERATIONS")
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError("CE_SEAT_WATCH_ITERATIONS must be an integer") from exc
    if value < 1:
        raise ConfigError("CE_SEAT_WATCH_ITERATIONS must be >= 1")
    return value


def _parse_seat_probes(raw: str) -> tuple[SeatProbeSpec, ...]:
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError("CE_SEAT_WATCH_SEAT_PROBES must be a JSON array") from exc
    if not isinstance(decoded, list) or not decoded:
        raise ConfigError("CE_SEAT_WATCH_SEAT_PROBES must be a non-empty JSON array")

    specs: list[SeatProbeSpec] = []
    for index, entry in enumerate(decoded):
        if not isinstance(entry, dict):
            raise ConfigError(f"seat probe at index {index} must be an object")
        seat_id = entry.get("seat_id")
        argv = entry.get("argv")
        if not isinstance(seat_id, str) or not seat_id.strip():
            raise ConfigError(f"seat probe at index {index} requires non-empty seat_id")
        if not isinstance(argv, list) or not argv:
            raise ConfigError(f"seat probe {seat_id} requires non-empty argv array")
        if any(not isinstance(part, str) or part == "" for part in argv):
            raise ConfigError(f"seat probe {seat_id} argv entries must be non-empty strings")
        specs.append(SeatProbeSpec(seat_id=seat_id, argv=tuple(argv)))
    return tuple(specs)


def _parse_dispatch_patterns(raw: str | None) -> tuple[str, ...]:
    if raw is None or raw == "":
        return ()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError("CE_SEAT_WATCH_DISPATCH_PATTERNS must be a JSON array") from exc
    if not isinstance(decoded, list):
        raise ConfigError("CE_SEAT_WATCH_DISPATCH_PATTERNS must be a JSON array")
    patterns: list[str] = []
    for index, item in enumerate(decoded):
        if not isinstance(item, str) or not item:
            raise ConfigError(f"dispatch pattern at index {index} must be a non-empty string")
        patterns.append(item)
    return tuple(patterns)


if __name__ == "__main__":  # pragma: no cover - exercised by python -m.
    raise SystemExit(main())
