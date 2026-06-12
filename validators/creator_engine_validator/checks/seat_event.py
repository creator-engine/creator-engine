"""Seat lifecycle sentinel event validation (ce-ops#26).

Validates every ``events.jsonl`` line (one JSON object per line) against
``schemas/seat-event.schema.yaml`` plus the per-event-kind conditional
requireds. The contract surface is instance-local (gitignored) at runtime;
``examples/well-formed/seat-events/`` and ``examples/malformed/seat-events/``
exercise the check in CI (the well-formed pass / malformed fail harness).

Thin by design: the engine lives in the **shared** ``seat_sentinel`` module
(imported by the v1 launchers and the v3 cockpit reader alike); this check is
just its registration. ``seat_sentinel`` imports nothing version-specific, so
the ``version_boundary`` ratchet stays green with no allowlist edit.
"""

from __future__ import annotations

from typing import Iterable

from .. import seat_sentinel
from ..reporting import CheckResult
from . import register

CHECK_NAME = seat_sentinel.CHECK_NAME


@register(
    CHECK_NAME,
    [
        seat_sentinel.CODE_SCHEMA,
        seat_sentinel.CODE_NOT_JSON,
        seat_sentinel.CODE_NOT_OBJECT,
    ],
)
def run(paths: Iterable[str]) -> CheckResult:
    return seat_sentinel.check_seat_events(paths)
