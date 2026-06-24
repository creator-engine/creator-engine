"""Shared GitHub Search API rate limiting helpers.

GitHub's Search API has a small per-credential budget, and CE runs several
pollers that can overlap on one host. This module uses a file-backed GCRA
token-bucket equivalent: every process reserves the next Search slot under an
OS lock, then sleeps outside the lock. The default rate is deliberately below
30/minute to leave headroom for manual/operator searches and clock jitter.

The module is boundary-neutral. v1 pickup code and v3 forge code can both use
it without importing across the v1/v3 runtime boundary.
"""
from __future__ import annotations

import json
import os
import random
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

try:  # pragma: no cover - exercised on the Linux gate, fallback is defensive.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

DEFAULT_SEARCH_RATE_PER_MINUTE = 24.0
DEFAULT_SEARCH_BURST = 1
DEFAULT_SEARCH_JITTER_SECONDS = 0.25
DEFAULT_SEARCH_MAX_ATTEMPTS = 3
DEFAULT_SEARCH_BACKOFF_SECONDS = 5.0

RATE_ENV = "CE_SEARCH_RATE_PER_MINUTE"
BURST_ENV = "CE_SEARCH_RATE_BURST"
JITTER_ENV = "CE_SEARCH_RATE_JITTER_SECONDS"
STATE_ENV = "CE_SEARCH_RATE_STATE"

T = TypeVar("T")
Sleep = Callable[[float], None]
Clock = Callable[[], float]
RandomFloat = Callable[[], float]


@dataclass
class SearchRateLimiter:
    """Cross-process Search API limiter with jittered retry support.

    The state file stores the GCRA theoretical arrival time (``tat``). GCRA is
    equivalent to a token bucket while needing one persisted timestamp, which
    keeps cross-process coordination small and fail-safe: corrupted state resets
    to an empty schedule instead of crashing a daemon.
    """

    state_path: Path
    rate_per_minute: float = DEFAULT_SEARCH_RATE_PER_MINUTE
    burst: int = DEFAULT_SEARCH_BURST
    jitter_seconds: float = DEFAULT_SEARCH_JITTER_SECONDS
    clock: Clock = time.time
    random_float: RandomFloat = random.random

    def __post_init__(self) -> None:
        if self.rate_per_minute <= 0:
            raise ValueError("rate_per_minute must be > 0")
        if self.burst < 1:
            raise ValueError("burst must be >= 1")
        if self.jitter_seconds < 0:
            raise ValueError("jitter_seconds must be >= 0")
        self.state_path = Path(self.state_path)

    @property
    def interval_seconds(self) -> float:
        return 60.0 / self.rate_per_minute

    def reserve_delay(self) -> float:
        """Reserve one Search request slot and return the required sleep."""
        base_delay = self._reserve_base_delay()
        jitter = self.random_float() * self.jitter_seconds if self.jitter_seconds else 0.0
        return max(0.0, base_delay + jitter)

    def wait(self, sleep: Sleep = time.sleep) -> float:
        """Reserve a slot and sleep for it, returning the delay used."""
        delay = self.reserve_delay()
        if delay > 0:
            sleep(delay)
        return delay

    def retry_delay(self, *, attempt: int, retry_after_seconds: int | float | None = None) -> float:
        """Return fail-safe backoff for a rate-limit response."""
        server_delay = float(retry_after_seconds or 0)
        exponential = DEFAULT_SEARCH_BACKOFF_SECONDS * (2 ** max(0, attempt - 1))
        jitter = self.random_float() * max(self.jitter_seconds, 1.0)
        return max(server_delay, exponential) + jitter

    def _reserve_base_delay(self) -> float:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("a+", encoding="utf-8") as fh:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                now = self.clock()
                state = self._read_state(fh)
                tat = _float_or_default(state.get("tat"), now)
                interval = self.interval_seconds
                burst_window = (self.burst - 1) * interval
                scheduled_at = max(now, tat - burst_window)
                new_tat = max(now, tat) + interval
                self._write_state(fh, {"tat": new_tat, "rate_per_minute": self.rate_per_minute})
                return max(0.0, scheduled_at - now)
            finally:
                if fcntl is not None:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _read_state(fh) -> dict[str, object]:
        try:
            fh.seek(0)
            text = fh.read()
            payload = json.loads(text) if text.strip() else {}
        except (OSError, TypeError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _write_state(fh, state: dict[str, object]) -> None:
        fh.seek(0)
        fh.truncate()
        json.dump(state, fh, sort_keys=True)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())


def call_with_search_api_headroom(
    operation: Callable[[], T],
    *,
    limiter: SearchRateLimiter,
    is_rate_limited: Callable[[BaseException], bool],
    retry_after_seconds: Callable[[BaseException], int | float | None] | None = None,
    max_attempts: int = DEFAULT_SEARCH_MAX_ATTEMPTS,
    sleep: Sleep = time.sleep,
) -> T:
    """Run a Search operation through the limiter and retry rate-limit failures."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    for attempt in range(1, max_attempts + 1):
        limiter.wait(sleep)
        try:
            return operation()
        except Exception as exc:
            if not is_rate_limited(exc) or attempt >= max_attempts:
                raise
            retry_after = retry_after_seconds(exc) if retry_after_seconds else None
            sleep(limiter.retry_delay(attempt=attempt, retry_after_seconds=retry_after))
    raise AssertionError("unreachable")


def default_search_rate_limiter() -> SearchRateLimiter:
    """Build the process-default shared limiter from environment overrides."""
    return SearchRateLimiter(
        state_path=_default_state_path(),
        rate_per_minute=_float_env(RATE_ENV, DEFAULT_SEARCH_RATE_PER_MINUTE),
        burst=max(1, _int_env(BURST_ENV, DEFAULT_SEARCH_BURST)),
        jitter_seconds=max(0.0, _float_env(JITTER_ENV, DEFAULT_SEARCH_JITTER_SECONDS)),
    )


def _default_state_path() -> Path:
    override = os.environ.get(STATE_ENV)
    if override and override.strip():
        return Path(override).expanduser()
    root = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return Path(root) / "creator-engine-search-api-rate.json"


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _float_or_default(value: object, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default
