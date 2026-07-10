"""Observe-only seat pane watcher for controller visibility."""

from __future__ import annotations

import dataclasses
import hashlib
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from .conveyor_discovery import (
    ProbeRunner,
    SeatProbeSpec,
    parse_ready_for_harvest_signals,
    subprocess_probe_runner,
)

SCHEMA_VERSION = "1"
BLOCKED_SIGNAL_PATTERN = re.compile(r"^\s*BLOCKED\s+(\S+)\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class WatchEvent:
    schema_version: str
    event_type: str
    seat_id: str
    ts: str
    poll_index: int
    detail: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


class SeatWatchDaemon:
    def __init__(
        self,
        specs: Sequence[SeatProbeSpec],
        *,
        idle_threshold_polls: int = 5,
        dispatch_patterns: Sequence[str] = (),
        probe_runner: ProbeRunner | None = None,
        now: Callable[[], str] | None = None,
    ) -> None:
        if idle_threshold_polls < 1:
            raise ValueError("idle_threshold_polls must be >= 1")
        self.specs = tuple(specs)
        self.idle_threshold_polls = idle_threshold_polls
        self.dispatch_patterns = tuple(dispatch_patterns)
        self.probe_runner = probe_runner or subprocess_probe_runner
        self.now = now or _utc_now
        self._pane_hashes: dict[str, str] = {}
        self._pane_texts: dict[str, str] = {}
        self._unchanged_counts: dict[str, int] = {}
        self._dispatch_missing_counts: dict[tuple[str, str], int] = {}

    def run_once(self, poll_index: int) -> list[WatchEvent]:
        """Run one poll pass. Returns all events from this pass."""

        events: list[WatchEvent] = []
        for spec in self.specs:
            try:
                pane_text = self.probe_runner(spec.argv)
            except Exception as exc:
                events.append(
                    self._event(
                        "pane_error",
                        spec.seat_id,
                        poll_index,
                        {
                            "error_class": classify_pane_error(exc),
                            "detail": _exception_detail(exc),
                        },
                    )
                )
                continue

            current_hash = hashlib.sha256(pane_text.encode("utf-8")).hexdigest()
            ready_events = self._ready_signal_events(spec.seat_id, pane_text, poll_index)
            blocked_events = self._blocked_signal_events(spec.seat_id, pane_text, poll_index)
            events.extend(ready_events)
            events.extend(blocked_events)

            signal_found = bool(ready_events or blocked_events)
            if signal_found:
                self._unchanged_counts[spec.seat_id] = 0
            else:
                idle_event = self._idle_event_if_ready(spec.seat_id, current_hash, poll_index)
                if idle_event is not None:
                    events.append(idle_event)

            events.extend(
                self._dispatch_events(
                    spec.seat_id,
                    pane_text,
                    current_hash,
                    poll_index,
                )
            )
            self._pane_hashes[spec.seat_id] = current_hash
            self._pane_texts[spec.seat_id] = pane_text

        return events

    def _ready_signal_events(
        self,
        seat_id: str,
        pane_text: str,
        poll_index: int,
    ) -> list[WatchEvent]:
        events: list[WatchEvent] = []
        for signal in parse_ready_for_harvest_signals(pane_text, seat_id=seat_id):
            events.append(
                self._event(
                    "ready_signal",
                    seat_id,
                    poll_index,
                    {
                        "branch": signal.branch,
                        "sha": signal.sha,
                        "tag": signal.tag,
                    },
                )
            )
        return events

    def _blocked_signal_events(
        self,
        seat_id: str,
        pane_text: str,
        poll_index: int,
    ) -> list[WatchEvent]:
        events: list[WatchEvent] = []
        for match in BLOCKED_SIGNAL_PATTERN.finditer(pane_text):
            events.append(
                self._event(
                    "blocked_signal",
                    seat_id,
                    poll_index,
                    {
                        "branch": match.group(1).strip(),
                        "reason": match.group(2).strip(),
                    },
                )
            )
        return events

    def _idle_event_if_ready(
        self,
        seat_id: str,
        current_hash: str,
        poll_index: int,
    ) -> WatchEvent | None:
        previous_hash = self._pane_hashes.get(seat_id)
        if previous_hash is None or current_hash == previous_hash:
            count = self._unchanged_counts.get(seat_id, 0) + 1
        else:
            count = 1
        self._unchanged_counts[seat_id] = count
        if count < self.idle_threshold_polls:
            return None

        self._unchanged_counts[seat_id] = 0
        return self._event(
            "idle_without_signal",
            seat_id,
            poll_index,
            {
                "polls_unchanged": count,
                "pane_hash": current_hash,
            },
        )

    def _dispatch_events(
        self,
        seat_id: str,
        pane_text: str,
        current_hash: str,
        poll_index: int,
    ) -> list[WatchEvent]:
        previous_text = self._pane_texts.get(seat_id, "")
        previous_lower = previous_text.lower()
        current_lower = pane_text.lower()
        events: list[WatchEvent] = []

        for pattern in self.dispatch_patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in current_lower and pattern_lower not in previous_lower:
                self._dispatch_missing_counts[(seat_id, pattern_lower)] = 0
                events.append(
                    self._event(
                        "dispatch_delivery_ack",
                        seat_id,
                        poll_index,
                        {
                            "pattern_matched": pattern,
                            "context_line": _context_line(pane_text, pattern_lower),
                        },
                    )
                )
                continue

            if pattern_lower in current_lower:
                self._dispatch_missing_counts[(seat_id, pattern_lower)] = 0
                continue

            key = (seat_id, pattern_lower)
            count = self._dispatch_missing_counts.get(key, 0) + 1
            self._dispatch_missing_counts[key] = count
            if count < self.idle_threshold_polls:
                continue

            self._dispatch_missing_counts[key] = 0
            events.append(
                self._event(
                    "dispatch_undelivered",
                    seat_id,
                    poll_index,
                    {
                        "pattern_expected": pattern,
                        "polls_without_ack": count,
                        "pane_hash": current_hash,
                    },
                )
            )
        return events

    def _event(
        self,
        event_type: str,
        seat_id: str,
        poll_index: int,
        detail: dict[str, object],
    ) -> WatchEvent:
        return WatchEvent(
            schema_version=SCHEMA_VERSION,
            event_type=event_type,
            seat_id=seat_id,
            ts=self.now(),
            poll_index=poll_index,
            detail=detail,
        )


def classify_pane_error(exc: Exception) -> str:
    if isinstance(exc, subprocess.CalledProcessError) and exc.returncode == 143:
        return "exit_143"

    message = str(exc).lower()
    if "rate limit" in message or "quota" in message or "429" in message:
        return "limit"
    if "unauthorized" in message or "401" in message or "authentication" in message:
        return "auth"
    if isinstance(exc, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
        return "probe_failed"
    return "unknown"


def _exception_detail(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:400]


def _context_line(pane_text: str, pattern_lower: str) -> str:
    for line in pane_text.splitlines():
        if pattern_lower in line.lower():
            return line[:200]
    return ""


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
