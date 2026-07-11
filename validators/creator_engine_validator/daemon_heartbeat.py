"""Shared, non-secret daemon heartbeat record and atomic latest-state emitter.

The emitter is deliberately passive: it never starts a thread, sleeps, probes a
process, or talks to systemd.  Daemon adoption layers call :meth:`emit` at
lifecycle boundaries and :meth:`emit_periodic_running` from their existing wait
or long-pass seams.  A structured journal sink is injected so unit tests and
non-systemd runtimes do not need journal access.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from .schema import load_schema

SCHEMA_VERSION: Final[int] = 1
SCHEMA_PATH: Final[str] = "schemas/daemon-heartbeat.schema.yaml"
JOURNAL_EVENT: Final[str] = "daemon_heartbeat"
_CONFIG_VALIDATION_TIME: Final[datetime] = datetime(1970, 1, 1, tzinfo=timezone.utc)

Clock = Callable[[], datetime]
JournalSink = Callable[[Mapping[str, Any]], None]


class DaemonHeartbeatError(ValueError):
    """A heartbeat could not be validated or emitted safely."""


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema(SCHEMA_PATH), format_checker=FormatChecker())


def validate_heartbeat(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a detached heartbeat mapping."""
    candidate = dict(record)
    errors = sorted(_validator().iter_errors(candidate), key=lambda error: list(error.path))
    if errors:
        raise DaemonHeartbeatError(_validation_message(errors[0])) from errors[0]
    return candidate


def read_heartbeat(path: str | Path) -> dict[str, Any]:
    """Read and validate an existing latest-state heartbeat."""
    target = Path(path)
    try:
        decoded = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DaemonHeartbeatError(f"cannot read daemon heartbeat {target}: {exc}") from exc
    if not isinstance(decoded, dict):
        raise DaemonHeartbeatError("daemon heartbeat must decode to an object")
    return validate_heartbeat(decoded)


class DaemonHeartbeatEmitter:
    """Atomically persist and journal the latest heartbeat for one daemon."""

    def __init__(
        self,
        path: str | Path,
        *,
        daemon_id: str,
        expected_interval_seconds: float | None = None,
        unit: str | None = None,
        scope: str | None = None,
        clock: Clock | None = None,
        journal_sink: JournalSink | None = None,
    ) -> None:
        self.path = Path(path)
        self.daemon_id = daemon_id
        self.expected_interval_seconds = expected_interval_seconds
        self.unit = unit
        self.scope = scope
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._journal_sink = journal_sink or (lambda _payload: None)
        self._last_pass_index = -1
        self._last_emitted_at: datetime | None = None

        # Validate identity/config before any filesystem side effect.
        validate_heartbeat(self._record("starting", 0, _CONFIG_VALIDATION_TIME))
        if self.path.exists():
            existing = read_heartbeat(self.path)
            self._verify_existing_identity(existing)
            self._last_pass_index = int(existing["pass_index"])
            self._last_emitted_at = _parse_utc(existing["ts"])

    @property
    def last_pass_index(self) -> int:
        return self._last_pass_index

    def emit(
        self,
        status: str,
        pass_index: int,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Validate, atomically replace, and journal one heartbeat."""
        emitted_at = _require_utc(now if now is not None else self._clock())
        record = validate_heartbeat(self._record(status, pass_index, emitted_at))
        if pass_index < self._last_pass_index:
            raise DaemonHeartbeatError(
                f"pass_index must be monotonic: {pass_index} < {self._last_pass_index}"
            )
        _atomic_write(self.path, record)
        self._journal_sink(_journal_payload(record))
        self._last_pass_index = pass_index
        self._last_emitted_at = emitted_at
        return record

    def emit_periodic_running(
        self,
        pass_index: int,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Emit ``running`` when the declared interval has elapsed.

        Callers invoke this from an existing wait/poll seam; this method never
        sleeps and never creates a background thread.
        """
        if self.expected_interval_seconds is None:
            raise DaemonHeartbeatError(
                "expected_interval_seconds is required for periodic running emission"
            )
        observed_at = _require_utc(now if now is not None else self._clock())
        if self._last_emitted_at is not None:
            elapsed = (observed_at - self._last_emitted_at).total_seconds()
            if elapsed < 0:
                raise DaemonHeartbeatError("heartbeat clock moved backwards")
            if elapsed < self.expected_interval_seconds:
                return None
        return self.emit("running", pass_index, now=observed_at)

    def _record(self, status: str, pass_index: int, emitted_at: datetime) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "daemon_id": self.daemon_id,
            "pass_index": pass_index,
            "ts": _format_utc(emitted_at),
            "status": status,
        }
        if self.expected_interval_seconds is not None:
            record["expected_interval_seconds"] = self.expected_interval_seconds
        if self.unit is not None:
            record["unit"] = self.unit
        if self.scope is not None:
            record["scope"] = self.scope
        return record

    def _verify_existing_identity(self, existing: Mapping[str, Any]) -> None:
        expected = self._record("starting", int(existing["pass_index"]), _parse_utc(existing["ts"]))
        for field in ("daemon_id", "expected_interval_seconds", "unit", "scope"):
            if existing.get(field) != expected.get(field):
                raise DaemonHeartbeatError(
                    f"existing heartbeat {field} does not match emitter configuration"
                )


def _atomic_write(path: Path, record: Mapping[str, Any]) -> None:
    if not path.parent.is_dir():
        raise DaemonHeartbeatError(f"heartbeat parent directory is missing: {path.parent}")
    payload = json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _fsync_directory(path: Path) -> None:
    directory_fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _journal_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "CE_EVENT": JOURNAL_EVENT,
        "CE_DAEMON_ID": record["daemon_id"],
        **dict(record),
    }


def _require_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise DaemonHeartbeatError("heartbeat clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return _require_utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DaemonHeartbeatError("heartbeat timestamp must be a UTC date-time ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DaemonHeartbeatError("heartbeat timestamp is invalid") from exc
    return _require_utc(parsed)


def _validation_message(error: JsonSchemaValidationError) -> str:
    location = ".".join(str(part) for part in error.path) or "record"
    return f"invalid daemon heartbeat at {location}: {error.message}"


__all__ = [
    "DaemonHeartbeatEmitter",
    "DaemonHeartbeatError",
    "JOURNAL_EVENT",
    "read_heartbeat",
    "validate_heartbeat",
]
