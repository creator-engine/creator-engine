"""Least-authority, durable model-canon observer.

Only the checked-in canon can select a container or command.  This module
observes; it never restarts, remediates, edits the canon, or reads credentials.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

from jsonschema import Draft202012Validator

from .daemon_lease import DEFAULT_LEASE_TTL_SECONDS, DaemonLeaseError, acquire
from .schema import load_schema

SCHEMA_PATH: Final = "schemas/model-canon.schema.yaml"
CANON_PROVENANCE_SHA256: Final = "59b9b8f2a8464dcb2050889cd557e669f9fe9212c9e346c5221b8cf722972fba"
DAEMON_NAME: Final = "model-drift-watcher"
JOURNAL_IDENTIFIER: Final = "ce-model-drift"
CADENCE_SECONDS: Final = 60.0
HEARTBEAT_SECONDS: Final = 30.0
_VERSION = re.compile(r"^codex\s+([0-9]+\.[0-9]+\.[0-9]+)\s*$")
_SAFE_SELECTORS: Final = frozenset({
    ("ce-dgx-codex", "/home/cedev4/.codex/config.toml"),
    ("ce-vps-codex", "/home/ce/.codex/config.toml"),
})


class ModelCanonError(ValueError):
    pass


class ModelDriftConfigError(ValueError):
    pass


@dataclass(frozen=True)
class CanonSeat:
    id: str
    container: str
    config_path: str
    model: str
    model_reasoning_effort: str
    codex_version: str


@dataclass(frozen=True)
class ModelCanon:
    provenance_sha256: str
    seats: tuple[CanonSeat, ...]


@dataclass(frozen=True)
class Observation:
    seat_id: str
    state: str
    observed_at: float
    detail: str = ""
    model: str | None = None
    effort: str | None = None
    version: str | None = None


def load_model_canon(path: str | Path) -> ModelCanon:
    """Load a schema-valid canon and reject any selector not proven by launchers."""
    try:
        import yaml
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ModelCanonError(f"cannot load model canon: {exc}") from exc
    errors = sorted(Draft202012Validator(load_schema(SCHEMA_PATH)).iter_errors(raw), key=lambda e: list(e.path))
    if errors:
        error = errors[0]
        location = ".".join(map(str, error.path)) or "canon"
        raise ModelCanonError(f"invalid model canon at {location}: {error.message}")
    assert isinstance(raw, dict)
    if raw["provenance_sha256"] != CANON_PROVENANCE_SHA256:
        raise ModelCanonError("model canon provenance does not match ratified routing")
    seats = tuple(CanonSeat(**item) for item in raw["seats"])
    if len({seat.id for seat in seats}) != len(seats):
        raise ModelCanonError("duplicate model canon seat id")
    selectors = {(seat.container, seat.config_path) for seat in seats}
    if len(selectors) != len(seats):
        raise ModelCanonError("duplicate model canon container/config selector")
    if not selectors <= _SAFE_SELECTORS:
        raise ModelCanonError("model canon selector is outside launcher-proven allowlist")
    return ModelCanon(raw["provenance_sha256"], seats)


def probe_seat(seat: CanonSeat, *, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run, now: float | None = None) -> Observation:
    """Use exactly two argv commands: config cat and ``codex --version``."""
    observed_at = time.time() if now is None else now
    if (seat.container, seat.config_path) not in _SAFE_SELECTORS:
        raise ModelCanonError("refusing observation outside fixed selector allowlist")
    kwargs = {"check": False, "capture_output": True, "text": True, "timeout": 10, "cwd": "/", "env": {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}}
    try:
        config = runner(["docker", "exec", seat.container, "cat", seat.config_path], **kwargs)
    except subprocess.TimeoutExpired:
        return Observation(seat.id, "unknown_timeout", observed_at, "config timeout")
    except OSError as exc:
        return Observation(seat.id, "unknown_command_failure", observed_at, str(exc))
    if config.returncode:
        return Observation(seat.id, _failure_kind(config.stderr), observed_at, "config command failed")
    try:
        data = tomllib.loads(config.stdout)
        model, effort = data["model"], data["model_reasoning_effort"]
        if not isinstance(model, str) or not isinstance(effort, str):
            raise ValueError("model fields must be strings")
    except (tomllib.TOMLDecodeError, KeyError, TypeError, ValueError) as exc:
        return Observation(seat.id, "unknown_malformed_config", observed_at, str(exc))
    try:
        version = runner(["docker", "exec", seat.container, "codex", "--version"], **kwargs)
    except subprocess.TimeoutExpired:
        return Observation(seat.id, "unknown_timeout", observed_at, "version timeout")
    except OSError as exc:
        return Observation(seat.id, "unknown_command_failure", observed_at, str(exc))
    if version.returncode:
        return Observation(seat.id, _failure_kind(version.stderr), observed_at, "version command failed")
    match = _VERSION.fullmatch(version.stdout)
    if match is None:
        return Observation(seat.id, "unknown_command_failure", observed_at, "malformed codex version")
    found = match.group(1)
    state = "model_drift" if model != seat.model else "effort_drift" if effort != seat.model_reasoning_effort else "version_drift" if found != seat.codex_version else "match"
    return Observation(seat.id, state, observed_at, model=model, effort=effort, version=found)


def _failure_kind(stderr: str) -> str:
    return "unknown_missing_container" if "no such container" in stderr.lower() else "unknown_command_failure"


class ModelDriftWatcher:
    """Apply one observation pass with two-hit/two-clear durable debounce."""
    def __init__(self, canon: ModelCanon, *, state_path: Path, inbox_path: Path, journal_sink: Callable[[Mapping[str, Any]], None] | None = None) -> None:
        self.canon, self.state_path, self.inbox_path = canon, state_path, inbox_path
        self.journal_sink = journal_sink or _stderr_journal
        self.state = _load_state(state_path)

    def observe(self, observations: Sequence[Observation]) -> list[dict[str, Any]]:
        expected, received = {seat.id for seat in self.canon.seats}, {item.seat_id for item in observations}
        if received != expected or len(received) != len(observations):
            raise ModelCanonError("observation pass must contain exactly one record per canon seat")
        alarms: list[dict[str, Any]] = []
        seats = self.state.setdefault("seats", {})
        for observation in observations:
            updated, alarm = _advance(dict(seats.get(observation.seat_id, {})), observation)
            seats[observation.seat_id] = updated
            if alarm:
                alarms.append(alarm)
        self.state["last_success_at"] = max(item.observed_at for item in observations)
        _atomic_json(self.state_path, self.state)
        for alarm in alarms:
            _append_ndjson(self.inbox_path, alarm)
            self.journal_sink(alarm)
        return alarms


def _advance(prior: dict[str, Any], observation: Observation) -> tuple[dict[str, Any], dict[str, Any] | None]:
    state = {"first_seen": None, "acknowledged": False, "active": False, "mismatch_count": 0, "match_count": 0, "drift_observations": 0, **prior}
    state["last_observation"] = asdict(observation)
    if observation.state.startswith("unknown_"):
        return state, None  # Unknown cannot reset an alert or masquerade as recovery.
    if observation.state == "match":
        state["match_count"] += 1
        state["mismatch_count"] = 0
        if state["active"] and state["match_count"] >= 2:
            state.update(active=False, first_seen=None, acknowledged=False, drift_observations=0)
        return state, None
    prior_observation = prior.get("last_observation", {})
    prior_at = prior_observation.get("observed_at") if prior_observation.get("state") != "match" else None
    if prior_at is None or observation.observed_at - float(prior_at) >= CADENCE_SECONDS:
        state["mismatch_count"] += 1
    state["match_count"] = 0
    if state["mismatch_count"] >= 2:
        if not state["active"]:
            state.update(active=True, first_seen=observation.observed_at, drift_observations=2)
        else:
            state["drift_observations"] += 1
    if state["active"] and not state["acknowledged"] and state["drift_observations"] == 3:
        return state, {"event": "model_drift_alarm", "journal_identifier": JOURNAL_IDENTIFIER, "seat_id": observation.seat_id, "state": observation.state, "first_seen": state["first_seen"], "observed_at": observation.observed_at, "observation": asdict(observation)}
    return state, None


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "seats": {}, "last_success_at": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelCanonError(f"cannot read model drift state: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("seats"), dict):
        raise ModelCanonError("model drift state is malformed")
    return data


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True); path.parent.chmod(0o700)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(value), sort_keys=True, separators=(",", ":")) + "\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
        path.chmod(0o600)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def _append_ndjson(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True); path.parent.chmod(0o700)
    with path.open("a", encoding="utf-8") as handle:
        os.chmod(path, 0o600); handle.write(json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n"); handle.flush(); os.fsync(handle.fileno())


def _stderr_journal(record: Mapping[str, Any]) -> None:
    print(json.dumps({"SYSLOG_IDENTIFIER": JOURNAL_IDENTIFIER, **dict(record)}, sort_keys=True), file=sys.stderr)


@dataclass(frozen=True)
class WatcherConfig:
    canon_path: Path; state_path: Path; lease_root: Path; inbox_path: Path; cadence_seconds: float = CADENCE_SECONDS


def load_config(env: Mapping[str, str] | None = None) -> WatcherConfig:
    source = dict(os.environ if env is None else env)
    allowed = {"CE_MODEL_DRIFT_CANON", "CE_MODEL_DRIFT_STATE_PATH", "CE_MODEL_DRIFT_LEASE_ROOT", "CE_MODEL_DRIFT_INBOX_PATH", "CE_MODEL_DRIFT_CADENCE_SECONDS"}
    forbidden = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "GH_", "GITHUB_", "BAO_", "VAULT_", "_PAT")
    if any(key not in allowed and any(marker in key.upper() for marker in forbidden) for key in source):
        raise ModelDriftConfigError("model drift environment must not contain credentials")
    unknown = {key for key in source if key.startswith("CE_MODEL_DRIFT_")} - allowed
    if unknown: raise ModelDriftConfigError(f"disallowed model drift environment keys: {sorted(unknown)}")
    def required(key: str) -> Path:
        path = Path(source.get(key, ""))
        if not source.get(key) or not path.is_absolute(): raise ModelDriftConfigError(f"{key} must be an absolute path")
        return path
    try: cadence = float(source.get("CE_MODEL_DRIFT_CADENCE_SECONDS", "60"))
    except ValueError as exc: raise ModelDriftConfigError("CE_MODEL_DRIFT_CADENCE_SECONDS must be 60") from exc
    if cadence != CADENCE_SECONDS: raise ModelDriftConfigError("CE_MODEL_DRIFT_CADENCE_SECONDS must be 60")
    return WatcherConfig(required("CE_MODEL_DRIFT_CANON"), required("CE_MODEL_DRIFT_STATE_PATH"), required("CE_MODEL_DRIFT_LEASE_ROOT"), required("CE_MODEL_DRIFT_INBOX_PATH"), cadence)


def main(env: Mapping[str, str] | None = None, *, iterations: int | None = None) -> int:
    try:
        config = load_config(env); canon = load_model_canon(config.canon_path)
        config.lease_root.mkdir(mode=0o700, parents=True, exist_ok=True); config.lease_root.chmod(0o700)
        lease = acquire(DAEMON_NAME, f"{DAEMON_NAME}:{os.getpid()}", state_root=config.lease_root, ttl_seconds=DEFAULT_LEASE_TTL_SECONDS)
    except (ModelCanonError, ModelDriftConfigError, DaemonLeaseError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2
    try:
        watcher, count = ModelDriftWatcher(canon, state_path=config.state_path, inbox_path=config.inbox_path), 0
        while iterations is None or count < iterations:
            watcher.observe([probe_seat(seat) for seat in canon.seats]); count += 1
            if iterations is None or count < iterations:
                time.sleep(HEARTBEAT_SECONDS); lease.heartbeat(); time.sleep(HEARTBEAT_SECONDS); lease.heartbeat()
    except (ModelCanonError, OSError, DaemonLeaseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1
    finally:
        lease.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
