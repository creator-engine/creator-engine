"""CE v3.5-D: the live usage tap — transcript → spend-ledger + token-rate (PURE core + 1 I/O edge).

This is the live ``usage`` tap that ``runner/spend_gate.py``'s docstring names as a
deferred seam (*"the live ``usage`` / ``/usage`` taps ... are deferred seams"*). It
reads a harness JSONL transcript, extracts per-turn token usage, and turns each
assistant turn into a ``runtime_spend_ledger`` record body **by reusing the existing
pure spend substrate** — :func:`spend_gate.compute_cost` (API-USD at live policy
rates) and :func:`spend_gate.meter_record_body` (the ledger-body builder). Cost is
NEVER reimplemented here, and an unpriced model is NEVER silently $0: it honors
:class:`spend_gate.UnknownModelRate` by routing that turn to ``unpriced_turns``.

Scope (v3.5-D.0.1/D.0.2): pure parse + pure projection-to-ledger-bodies + pure
token-rate fold + ONE thin file-read edge (:func:`tap_transcript_file`). Out of
scope (later slices): running the tap over the live fleet to produce the artifact
number (D.0.3), and any spine write / live drive-loop wiring / in-product
v3-driven-run tap.

**PURE core.** :func:`parse_transcript_usage` and :func:`usage_turns_to_ledger` do NO
I/O — no disk, no subprocess, no socket, no wall-clock, no rng. The only file read is
isolated in :func:`tap_transcript_file`. Stdlib ``json`` only; no new deps.

Defensive only — it measures the Creator Engine's own runtime spend; never offensive.

See:
  - ``runner/spend_gate.py`` (``compute_cost`` / ``meter_record_body`` / ``UnknownModelRate``)
  - ``schemas/runtime-policy.schema.yaml`` (the ``model_rates`` table, read live from policy)
  - ``schemas/runtime-evidence.schema.yaml`` (the ``runtime_spend_ledger`` record)
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .spend_gate import UnknownModelRate, _parse_ts, _span_hours, compute_cost, meter_record_body

#: The cost-relevant subset of a transcript ``usage`` object — the only keys
#: :func:`spend_gate.compute_cost` consumes. Every other usage key (``server_tool_use``,
#: ``service_tier``, ``cache_creation``, ``iterations``, ...) is carried by the
#: transcript but irrelevant to cost and is dropped here.
_COST_USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


@dataclass(frozen=True)
class UsageTurn:
    """One assistant turn's metered usage, lifted from a transcript record (PURE value).

    ``usage`` carries ONLY the 4-key cost subset (:data:`_COST_USAGE_KEYS`) — the shape
    :func:`spend_gate.compute_cost` consumes — never the full transcript usage blob.
    """

    session_id: str
    model: str
    recorded_at: str
    usage: dict


@dataclass(frozen=True)
class FleetUsage:
    """Fleet-level token projection over selected usage turns (PURE)."""

    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    total_tokens: int
    turn_count: int
    span_hours: Decimal | None
    tokens_per_hour: Decimal | None


def _cost_subset(usage: dict[str, Any]) -> dict:
    """Project a transcript usage object down to the 4 cost keys (PURE)."""
    return {key: usage[key] for key in _COST_USAGE_KEYS if key in usage}


def parse_transcript_usage(lines: Iterable[str]) -> list[UsageTurn]:
    """Parse harness JSONL ``lines`` into one :class:`UsageTurn` per metered assistant turn (PURE).

    Tolerant + idempotent: emits a turn only for an **assistant** record bearing a
    usage object that carries ``input_tokens``/``output_tokens``. **Skips** (never
    raises) malformed JSON, non-assistant records, records with no usage,
    ``isSidechain`` turns, and records with no model. Does NO I/O — feed it lines from
    :func:`tap_transcript_file` (or any in-memory iterable).
    """
    turns: list[UsageTurn] = []
    for line in lines:
        text = (line or "").strip()
        if not text:
            continue
        try:
            record = json.loads(text)
        except (ValueError, TypeError):
            continue
        if not isinstance(record, dict):
            continue
        if record.get("type") != "assistant":
            continue
        if record.get("isSidechain") is True:
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        model = message.get("model")
        if not model:
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        # A usage object with neither token count is not a metered turn (e.g. a
        # tool-only continuation); 0 is a valid count, so test presence, not truth.
        if usage.get("input_tokens") is None and usage.get("output_tokens") is None:
            continue
        turns.append(
            UsageTurn(
                session_id=record.get("sessionId") or "",
                model=str(model),
                recorded_at=record.get("timestamp") or "",
                usage=_cost_subset(usage),
            )
        )
    return turns


def usage_turns_to_ledger(
    turns: Iterable[UsageTurn],
    *,
    model_rates: Any,
    fleet_id: str,
    policy_sha: str = "",
    run_id_of: Callable[[UsageTurn], str] | None = None,
) -> tuple[list[dict], list[UsageTurn]]:
    """Project metered turns into ``runtime_spend_ledger`` bodies, reusing ``spend_gate`` (PURE).

    For each turn: ``cost = spend_gate.compute_cost(turn.usage, turn.model,
    model_rates)`` at the live policy ``model_rates``, then a body via
    :func:`spend_gate.meter_record_body`. ``run_id`` defaults to the turn's
    ``session_id`` (override with ``run_id_of``). Returns ``(ledger_bodies,
    unpriced_turns)``: a turn whose model has no rate row
    (:class:`spend_gate.UnknownModelRate`) is routed to ``unpriced_turns`` — NEVER a
    silent $0, honoring spend_gate's discipline. Cost is NOT reimplemented here. The
    caller appends each body to a ``runtime_evidence_spine`` (a deferred seam — this
    slice only builds the bodies).
    """
    ledger_bodies: list[dict] = []
    unpriced_turns: list[UsageTurn] = []
    for turn in turns:
        try:
            cost: Decimal = compute_cost(turn.usage, turn.model, model_rates)
        except UnknownModelRate:
            unpriced_turns.append(turn)
            continue
        run_id = run_id_of(turn) if run_id_of is not None else turn.session_id
        ledger_bodies.append(
            meter_record_body(
                policy_sha=policy_sha,
                run_id=run_id,
                recorded_at=turn.recorded_at,
                amount=cost,
                unit="$",
                fleet_id=fleet_id,
                model=turn.model,
            )
        )
    return ledger_bodies, unpriced_turns


def _token_count(usage: dict, key: str) -> int:
    try:
        return int(usage.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _turn_inside_wall_clock_window(turn: UsageTurn, since: str | None, until: str | None) -> bool:
    since_dt = _parse_ts(since)
    until_dt = _parse_ts(until)
    if since_dt is None and until_dt is None:
        return True
    recorded_dt = _parse_ts(turn.recorded_at)
    if recorded_dt is None:
        return False
    if since_dt is not None and recorded_dt < since_dt:
        return False
    if until_dt is not None and recorded_dt > until_dt:
        return False
    return True


def fleet_token_rate(
    turns: Iterable[UsageTurn],
    *,
    since: str | None = None,
    until: str | None = None,
) -> FleetUsage:
    """Project selected usage turns into fleet token totals and tokens/hour (PURE).

    The caller pre-selects the fleet's turns; :class:`UsageTurn` intentionally has
    no ``fleet_id`` field. Cache tokens are included in ``total_tokens`` because
    they are part of the metered usage subset that drives cost.
    """
    filtered = [turn for turn in turns or [] if _turn_inside_wall_clock_window(turn, since, until)]
    input_tokens = sum(_token_count(turn.usage, "input_tokens") for turn in filtered)
    output_tokens = sum(_token_count(turn.usage, "output_tokens") for turn in filtered)
    cache_creation_input_tokens = sum(
        _token_count(turn.usage, "cache_creation_input_tokens") for turn in filtered
    )
    cache_read_input_tokens = sum(
        _token_count(turn.usage, "cache_read_input_tokens") for turn in filtered
    )
    total_tokens = (
        input_tokens
        + output_tokens
        + cache_creation_input_tokens
        + cache_read_input_tokens
    )
    bounded_span = _span_hours([since, until]) if since is not None and until is not None else None
    span_hours = bounded_span if bounded_span is not None else _span_hours(turn.recorded_at for turn in filtered)
    tokens_per_hour = Decimal(total_tokens) / span_hours if span_hours is not None and span_hours > 0 else None
    return FleetUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
        total_tokens=total_tokens,
        turn_count=len(filtered),
        span_hours=span_hours,
        tokens_per_hour=tokens_per_hour,
    )


def tap_transcript_file(path: Any) -> list[UsageTurn]:
    """Read a transcript file and parse it into :class:`UsageTurn`s (the ONLY I/O edge).

    The sole disk touch in this module: it opens/reads ``path`` and delegates to the
    pure :func:`parse_transcript_usage`. All parsing stays pure; the read is isolated
    here so the core remains testable without a filesystem.
    """
    with open(path, encoding="utf-8") as handle:
        return parse_transcript_usage(handle)
