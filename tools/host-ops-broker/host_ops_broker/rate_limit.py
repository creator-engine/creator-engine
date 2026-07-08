"""In-memory per-caller per-target rate limiting for host-ops broker v1."""
from __future__ import annotations

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.limit < 0:
            raise ValueError("limit must be >= 0")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    key: str
    limit: int
    window_seconds: int
    used: int


DEFAULT_RATE_LIMITS: dict[str, RateLimitRule] = {
    "status": RateLimitRule(30, 60),
    "restart-daemon": RateLimitRule(3, 15 * 60),
    "prepare-owned-state-root": RateLimitRule(6, 60 * 60),
    "rotate-attempt-log": RateLimitRule(6, 60 * 60),
    "repair-systemd-unit": RateLimitRule(3, 15 * 60),
    "run-ephemeral-container": RateLimitRule(3, 60 * 60),
    "prune-stopped-owned-containers": RateLimitRule(3, 60 * 60),
    "snapshot-openbao": RateLimitRule(2, 60 * 60),
    "restore-drill-openbao": RateLimitRule(1, 6 * 60 * 60),
}


class InMemoryRateLimiter:
    """Deterministic in-process limiter for tests and library embedding."""

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
        store: MutableMapping[str, list[float]] | None = None,
        rules: dict[str, RateLimitRule] | None = None,
    ) -> None:
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._store = store if store is not None else {}
        self._rules = dict(DEFAULT_RATE_LIMITS)
        if rules:
            self._rules.update(rules)

    def key(self, caller_identity: str, verb: str, target: str) -> str:
        return f"{caller_identity}:{verb}:{target}"

    def check_and_record(self, caller_identity: str, verb: str, target: str) -> RateLimitDecision:
        rule = self._rules[verb]
        key = self.key(caller_identity, verb, target)
        now_ts = self._timestamp()
        cutoff = now_ts - rule.window_seconds
        entries = [ts for ts in self._store.get(key, []) if ts > cutoff]
        if len(entries) >= rule.limit:
            self._store[key] = entries
            return RateLimitDecision(False, key, rule.limit, rule.window_seconds, len(entries))
        entries.append(now_ts)
        self._store[key] = entries
        return RateLimitDecision(True, key, rule.limit, rule.window_seconds, len(entries))

    def _timestamp(self) -> float:
        dt = self._now()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).timestamp()
