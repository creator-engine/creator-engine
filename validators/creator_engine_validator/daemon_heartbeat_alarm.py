"""Read-only daemon-heartbeat classification and bounded alarm journaling."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

from .daemon_heartbeat import DaemonHeartbeatError, read_heartbeat

DEFAULT_EXPECTED_DAEMONS: Final[tuple[str, ...]] = ("belt", "integrator", "review-pickup")
DEFAULT_GRACE_FACTOR: Final[float] = 3.0
DEFAULT_STATE_DIR: Final[Path] = Path.home() / ".local" / "state" / "creator-engine" / "daemon-heartbeats"
ALARM_WINDOW_SECONDS: Final[float] = 300.0


def configuration_from_environment(environ: Mapping[str, str] | None = None) -> tuple[Path, float, tuple[str, ...]]:
    """Return safe inputs, retaining documented defaults for bad overrides."""
    env = os.environ if environ is None else environ
    state_dir = Path(env.get("CE_HEARTBEAT_STATE_DIR", str(DEFAULT_STATE_DIR)))
    try:
        grace = float(env.get("CE_HEARTBEAT_GRACE_FACTOR", str(DEFAULT_GRACE_FACTOR)))
    except ValueError:
        grace = DEFAULT_GRACE_FACTOR
    if not 0 < grace <= 1000:
        grace = DEFAULT_GRACE_FACTOR
    raw_expected = env.get("CE_HEARTBEAT_EXPECTED_DAEMONS")
    expected = tuple(item.strip() for item in raw_expected.split(",") if item.strip()) if raw_expected else DEFAULT_EXPECTED_DAEMONS
    if not expected or len(set(expected)) != len(expected) or any(not _valid_id(item) for item in expected):
        expected = DEFAULT_EXPECTED_DAEMONS
    return state_dir, grace, expected


def check_heartbeats(state_dir: Path, *, grace_factor: float, expected_daemons: Iterable[str], now: datetime | None = None) -> dict[str, Any]:
    """Classify every heartbeat file and independently report absent expected ids."""
    observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    entries: dict[str, dict[str, Any]] = {}
    if state_dir.is_dir():
        for path in sorted(state_dir.glob("*.json")):
            daemon_id = path.stem
            try:
                record = read_heartbeat(path)
                daemon_id = str(record["daemon_id"])
                entries[daemon_id] = _classify(record, grace_factor, observed_at)
            except DaemonHeartbeatError as exc:
                entries[daemon_id] = {"daemon_id": daemon_id, "state": "FAILED", "cause": str(exc), "age_seconds": None, "threshold_seconds": None}
    for daemon_id in expected_daemons:
        entries.setdefault(daemon_id, {"daemon_id": daemon_id, "state": "MISSING", "cause": "heartbeat is absent", "age_seconds": None, "threshold_seconds": None})
    daemons = [entries[key] for key in sorted(entries)]
    return {"ok": all(entry["state"] == "OK" for entry in daemons), "checked_at": _format_time(observed_at), "daemons": daemons}


def append_new_alarms(report: Mapping[str, Any], inbox_path: Path, *, now: datetime | None = None) -> list[dict[str, Any]]:
    """Append only alarm tuples not seen within the short bounded window."""
    observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    prior = _recent_alarm_keys(inbox_path, observed_at)
    additions = []
    for entry in report["daemons"]:
        if entry["state"] == "OK":
            continue
        key = (entry["daemon_id"], entry["cause"])
        if key not in prior:
            additions.append({"event": "daemon_heartbeat_alarm", "alarmed_at": _format_time(observed_at), **entry})
            prior.add(key)
    if additions:
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        with inbox_path.open("a", encoding="utf-8") as handle:
            for entry in additions:
                handle.write(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")
    return additions


def _classify(record: Mapping[str, Any], grace_factor: float, now: datetime) -> dict[str, Any]:
    timestamp = datetime.fromisoformat(str(record["ts"]).replace("Z", "+00:00"))
    age = max(0.0, (now - timestamp).total_seconds())
    threshold = float(record.get("expected_interval_seconds", 60)) * grace_factor
    status = str(record["status"])
    if status in {"failed", "stopping"} and age > threshold:
        state, cause = "FAILED", f"status {status} persisted beyond grace"
    elif age > threshold:
        state, cause = "STALE", "heartbeat age exceeds grace threshold"
    elif status in {"running", "pass_complete"}:
        state, cause = "OK", "fresh heartbeat"
    else:
        state, cause = "FAILED", f"status {status} is not healthy"
    return {"daemon_id": record["daemon_id"], "state": state, "cause": cause, "age_seconds": round(age, 3), "threshold_seconds": threshold}


def _recent_alarm_keys(path: Path, now: datetime) -> set[tuple[str, str]]:
    if not path.is_file():
        return set()
    keys = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-256:]
    except OSError:
        return keys
    for line in lines:
        try:
            entry = json.loads(line)
            timestamp = datetime.fromisoformat(str(entry["alarmed_at"]).replace("Z", "+00:00"))
            if now - timestamp <= timedelta(seconds=ALARM_WINDOW_SECONDS):
                keys.add((str(entry["daemon_id"]), str(entry["cause"])))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return keys


def _valid_id(value: str) -> bool:
    return len(value) >= 3 and value[0].islower() and all(char.islower() or char.isdigit() or char == "-" for char in value)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
