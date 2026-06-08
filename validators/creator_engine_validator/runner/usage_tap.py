"""CE v3.5-D.0.1: the live usage tap — harness transcript → spend-ledger (PURE core + 1 I/O edge).

This is the live ``usage`` tap that ``runner/spend_gate.py``'s docstring names as a
deferred seam (*"the live ``usage`` / ``/usage`` taps ... are deferred seams"*). It
reads a harness JSONL transcript, extracts per-turn token usage, and turns each
assistant turn into a ``runtime_spend_ledger`` record body **by reusing the existing
pure spend substrate** — :func:`spend_gate.compute_cost` (API-USD at live policy
rates) and :func:`spend_gate.meter_record_body` (the ledger-body builder). Cost is
NEVER reimplemented here, and an unpriced model is NEVER silently $0: it honors
:class:`spend_gate.UnknownModelRate` by routing that turn to ``unpriced_turns``.

Scope (v3.5-D.0.1): pure parse + pure projection-to-ledger-bodies + ONE thin
file-read edge (:func:`tap_transcript_file`). Out of scope (later slices): fleet
aggregation across sessions + the tokens/hr time-window meter (D.0.2), running the tap
over the live fleet to produce the artifact number (D.0.3), and any spine write /
live drive-loop wiring / in-product v3-driven-run tap.

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

from .spend_gate import UnknownModelRate, compute_cost, meter_record_body

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


def tap_transcript_file(path: Any) -> list[UsageTurn]:
    """Read a transcript file and parse it into :class:`UsageTurn`s (the ONLY I/O edge).

    The sole disk touch in this module: it opens/reads ``path`` and delegates to the
    pure :func:`parse_transcript_usage`. All parsing stays pure; the read is isolated
    here so the core remains testable without a filesystem.
    """
    with open(path, encoding="utf-8") as handle:
        return parse_transcript_usage(handle)
