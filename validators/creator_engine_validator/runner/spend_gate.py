"""CE v3 plane-C tokenomics: the spend gate (admission + circuit-breaker) — PURE.

The stateful spend governance layer that reuses the G-4 action-gate's escalation +
evidence machinery, with ``spend`` as another deny-by-default blast-radius axis.

It is a *different kind* of gate than the G-4 action gate. The action gate
(``runner.audit_overlay.decide``) is stateless / per-event ("is this allowed?",
pure ``classify``); the spend gate is **stateful / cumulative** ("is there budget
left?", needs a ledger + a threshold). So it is a ledger projection + an admission
check + a circuit-breaker — NOT a ``classify()`` branch.

Design (the PINNED tokenomics design, Forks A-C):

* **Fork A — enforcement model.** An **admission gate** (refuse a run whose
  envelope is already exhausted, *before* provision) + a **post-action
  circuit-breaker** (meter spend as reported, trip when cumulative crosses the
  cap). No per-action pre-estimation — an LLM call's cost is unknown until it
  returns.
* **Fork B — budget hierarchy.** Nested **deny-by-default** envelopes
  ``global -> fleet -> run``, **most-restrictive-wins** (a run admits only if every
  enclosing envelope has headroom). ``max_concurrent_runs`` is a second,
  concurrency envelope dimension.
* **Fork C — billing-tier-aware metric, two disjoint regimes.** Fleet -> API-USD
  (computed from a ``usage`` object x per-model rates); subscription/OAuth seat ->
  single-seat ``%``-meter (never a fleet scope).

**State-as-projection.** There is no mutable ledger file: the cumulative tally is
:func:`project_spend`, a PURE fold over the spend-ledger leaves on the existing
hash-chained ``runtime_evidence_spine`` (faithful + tamper-evident, reusing
``verify_chain``). The breaker reads the projection after each metered leaf.

**Faithful-by-construction.** Cost is transport / API-reported, never
agent-asserted -> it inherits the Fork-1 fidelity (the agent cannot spoof its own
spend). This module NEVER trusts an agent-supplied number; it meters a ``usage``
report against rates READ LIVE from policy (never a baked vendor constant).

**PURE.** Every function here is pure — no disk, no subprocess, no socket, no
wall-clock read, no rng. ``recorded_at`` is an input. The live ``usage`` /
``/usage`` taps, the live cockpit escalation channel, and the cross-process
concurrency semaphore are deferred seams (this lands the pure decision substrate).

Defensive only — it caps the Creator Engine's own runtime spend; never offensive.

See:
  - ``docs/contracts/spend-envelope.md``
  - ``schemas/runtime-policy.schema.yaml`` (the spend-envelope policy fields)
  - ``schemas/runtime-evidence.schema.yaml`` (the spend-ledger / breach records)
  - ``runner/audit_overlay.py`` (the G-4 ``decide()`` machinery this composes with)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from ..runtime_evidence_spine import (
    RUNTIME_SPEND_BREACH_RECORD_KIND,
    RUNTIME_SPEND_BREACH_RECORD_TYPE,
    RUNTIME_SPEND_LEDGER_RECORD_KIND,
    RUNTIME_SPEND_LEDGER_RECORD_TYPE,
)
from .audit_overlay import ALLOWED, DENIED, ESCALATE, Decision, decide

#: The soft-alert tripwire ratio (~80%) — a structural CE design threshold (a
#: ratio of a configured cap), NOT a vendor price; overridable per call. The hard
#: breaker trips at ratio >= 1.0.
SOFT_BREACH_RATIO = Decimal("0.8")

#: The documented cache-read price RATIO (0.1x input) — a ratio, not an expiring
#: absolute price, so it is safe to default when a rate row omits it.
CACHE_READ_RATIO = Decimal("0.1")

#: Tokens-per-MTok divisor (rates are quoted per million tokens).
_MTOK = Decimal(1_000_000)

#: The two-signal refusal protocol (cf. Portkey 412-vs-429).
SIGNAL_OK = "ok"
SIGNAL_BUDGET_EXHAUSTED = "budget_exhausted"  # do NOT retry
SIGNAL_THROTTLE = "throttle"  # retry with backoff


class UnknownModelRate(ValueError):
    """Raised when :func:`compute_cost` has no rate row for the metered model.

    A missing rate is a policy/config error (rates are read live from policy); the
    admission/metering caller treats it as a refuse-or-escalate, never as $0.
    """


@dataclass(frozen=True)
class SpendDecision:
    """The verdict of an admission / breaker check (mirrors the G-4 ``Decision``).

    ``verdict`` is the enforced outcome (``allowed``/``denied``/``escalate``);
    ``signal`` is the two-signal refusal code (``ok``/``budget_exhausted``/
    ``throttle``); ``scope`` is the envelope level that tripped; ``tier`` is the
    breaker tier (``""``/``soft``/``hard``); ``escalation_id`` is a deterministic,
    value-free digest present only for a ``hard`` pause+escalate.
    """

    verdict: str
    signal: str
    reason: str
    scope: str = ""
    tier: str = ""
    escalation_id: str | None = None


@dataclass(frozen=True)
class FleetSpendMeter:
    """Fleet-level spend projection over runtime spend-ledger leaves (PURE)."""

    fleet_id: str | None
    unit: str
    spend: Decimal
    record_count: int
    run_count: int
    span_hours: Decimal | None
    spend_per_hour: Decimal | None


# ---------------------------------------------------------------------------
# Cost metering — the two regimes (PURE; rates/meters are inputs, never baked)
# ---------------------------------------------------------------------------
def _dec(value: Any) -> Decimal:
    """Coerce a JSON number to Decimal without binary-float error (PURE)."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value if value is not None else 0))


def _find_rate(model: str, model_rates: Any) -> dict[str, Any]:
    for row in model_rates or []:
        if isinstance(row, dict) and row.get("model") == model:
            return row
    raise UnknownModelRate(f"no model_rates row for model {model!r} (rates are read live from policy)")


def compute_cost(usage: dict[str, Any], model: str, model_rates: Any) -> Decimal:
    """Return the API-USD cost of one ``usage`` report at the live per-model rates (PURE).

    ``usage`` is the transport/API-reported token object
    (``input_tokens`` / ``output_tokens`` / ``cache_creation_input_tokens`` /
    ``cache_read_input_tokens``); ``model_rates`` is the policy's live rate table.
    Cache-read defaults to the documented :data:`CACHE_READ_RATIO` of the input
    rate, and cache-creation to the input rate, when a row omits them. Raises
    :class:`UnknownModelRate` for an unpriced model (never silently $0).
    """
    rate = _find_rate(model, model_rates)
    in_rate = _dec(rate.get("input_per_mtok"))
    out_rate = _dec(rate.get("output_per_mtok"))
    cache_read_rate = (
        _dec(rate.get("cache_read_per_mtok"))
        if rate.get("cache_read_per_mtok") is not None
        else in_rate * CACHE_READ_RATIO
    )
    cache_write_rate = (
        _dec(rate.get("cache_write_per_mtok"))
        if rate.get("cache_write_per_mtok") is not None
        else in_rate
    )
    u = usage or {}
    cost = (
        _dec(u.get("input_tokens")) * in_rate
        + _dec(u.get("output_tokens")) * out_rate
        + _dec(u.get("cache_read_input_tokens")) * cache_read_rate
        + _dec(u.get("cache_creation_input_tokens")) * cache_write_rate
    ) / _MTOK
    return cost


def seat_usage_pct(meter: dict[str, Any], window: str) -> Decimal:
    """Return the single-seat utilization ``%`` for ``window`` (the subscription regime, PURE).

    ``meter`` is the ``/usage``-shaped report ``{window: {used, limit}}`` (read
    live; never poolable across seats). Returns ``used / limit * 100`` for the
    window, or ``0`` when the window/limit is absent. The live ``/usage`` tap is a
    deferred seam — here the meter is a value.
    """
    window_meter = (meter or {}).get(window)
    if not isinstance(window_meter, dict):
        return Decimal(0)
    limit = _dec(window_meter.get("limit"))
    if limit <= 0:
        return Decimal(0)
    return _dec(window_meter.get("used")) / limit * Decimal(100)


# ---------------------------------------------------------------------------
# The ledger projection — state-as-projection over the spine (PURE)
# ---------------------------------------------------------------------------
def project_spend(
    records: Any,
    scope: str,
    *,
    fleet_id: str | None = None,
    run_id: str | None = None,
    unit: str = "$",
    window: str | None = None,
) -> Decimal:
    """Fold the spend-ledger leaves on a chain into a cumulative tally (PURE).

    Reads only ``runtime_spend_ledger`` records (ignores every other record type on
    the same chain), summing ``amount`` for the requested ``scope`` / ``unit`` /
    ``window``. Scope roll-up: ``run`` -> leaves whose ``run_id`` matches; ``fleet``
    -> leaves whose ``fleet_id`` matches; ``global`` -> every leaf (the nested
    deny-by-default hierarchy). ``window`` filters when given (a leaf with no window
    tag is counted). Accepts raw record bodies OR sealed chain records — it reads
    only semantic fields. The cross-run global/fleet fold is O(history); an
    incremental derived cache is a deferred efficiency follow-on.
    """
    total = Decimal(0)
    for record in records or []:
        if not isinstance(record, dict):
            continue
        if record.get("record_type") != RUNTIME_SPEND_LEDGER_RECORD_TYPE:
            continue
        if record.get("unit") != unit:
            continue
        if window is not None and record.get("window") not in (None, window):
            continue
        if scope == "run" and run_id is not None and record.get("run_id") != run_id:
            continue
        if scope == "fleet" and fleet_id is not None and record.get("fleet_id") != fleet_id:
            continue
        total += _dec(record.get("amount"))
    return total


def _parse_ts(value: Any) -> datetime | None:
    """Parse an input ISO-8601 timestamp, accepting a trailing ``Z`` (PURE)."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _span_hours(timestamps: Any) -> Decimal | None:
    """Return the positive hour span across parseable input timestamps (PURE)."""
    parsed = [_parse_ts(value) for value in timestamps or []]
    points = [value for value in parsed if value is not None]
    if len(points) < 2:
        return None
    delta = max(points) - min(points)
    seconds = (
        Decimal(delta.days * 86_400 + delta.seconds)
        + Decimal(delta.microseconds) / Decimal(1_000_000)
    )
    if seconds <= 0:
        return None
    return seconds / Decimal(3_600)


def _inside_wall_clock_window(recorded_at: Any, since: Any, until: Any) -> bool:
    since_dt = _parse_ts(since)
    until_dt = _parse_ts(until)
    if since_dt is None and until_dt is None:
        return True
    recorded_dt = _parse_ts(recorded_at)
    if recorded_dt is None:
        return False
    if since_dt is not None and recorded_dt < since_dt:
        return False
    if until_dt is not None and recorded_dt > until_dt:
        return False
    return True


def _fleet_spend_records(
    records: Any,
    *,
    fleet_id: str | None,
    unit: str,
    window: str | None,
    since: Any,
    until: Any,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        if record.get("record_type") != RUNTIME_SPEND_LEDGER_RECORD_TYPE:
            continue
        if record.get("unit") != unit:
            continue
        if window is not None and record.get("window") not in (None, window):
            continue
        if fleet_id is not None and record.get("fleet_id") != fleet_id:
            continue
        if not _inside_wall_clock_window(record.get("recorded_at"), since, until):
            continue
        out.append(record)
    return out


def fleet_spend_meter(
    records: Any,
    *,
    fleet_id: str | None = None,
    unit: str = "$",
    window: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> FleetSpendMeter:
    """Project fleet spend and spend/hour from spend-ledger leaves (PURE).

    ``window`` is the ledger accounting tag. ``since``/``until`` are optional
    wall-clock bounds over ``recorded_at``; when present, the total and rate are
    computed from the same filtered leaf set.
    """
    leaves = _fleet_spend_records(
        records,
        fleet_id=fleet_id,
        unit=unit,
        window=window,
        since=since,
        until=until,
    )
    if since is None and until is None:
        scope = "global" if fleet_id is None else "fleet"
        spend = project_spend(records, scope, fleet_id=fleet_id, unit=unit, window=window)
    else:
        spend = sum((_dec(record.get("amount")) for record in leaves), Decimal(0))
    bounded_span = _span_hours([since, until]) if since is not None and until is not None else None
    span_hours = bounded_span if bounded_span is not None else _span_hours(record.get("recorded_at") for record in leaves)
    spend_per_hour = spend / span_hours if span_hours is not None and span_hours > 0 else None
    return FleetSpendMeter(
        fleet_id=fleet_id,
        unit=unit,
        spend=spend,
        record_count=len(leaves),
        run_count=len({record.get("run_id") for record in leaves if record.get("run_id")}),
        span_hours=span_hours,
        spend_per_hour=spend_per_hour,
    )


# ---------------------------------------------------------------------------
# Admission gate (Fork A) — refuse an already-exhausted envelope, before provision
# ---------------------------------------------------------------------------
def _iter_envelopes(envelopes: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for env in envelopes or []:
        if isinstance(env, dict) and env.get("scope") and env.get("unit"):
            out.append(env)
    return out


#: Innermost-first scope order, so "most-restrictive-wins" reports the tightest.
_SCOPE_ORDER = {"run": 0, "fleet": 1, "global": 2}


def admit(
    envelopes: Any,
    records: Any,
    *,
    run_id: str | None = None,
    fleet_id: str | None = None,
) -> SpendDecision:
    """Admit a run iff every enclosing envelope has headroom (most-restrictive-wins, PURE).

    Refuses (``budget_exhausted`` — do NOT retry) when any envelope's cumulative
    projection is already at/over its cap, reporting the innermost (tightest) one.
    No per-action pre-estimation (Fork A): admission tests the *already-incurred*
    spend, not the next call's cost.
    """
    for env in sorted(_iter_envelopes(envelopes), key=lambda e: _SCOPE_ORDER.get(e.get("scope"), 9)):
        scope = str(env.get("scope"))
        unit = str(env.get("unit"))
        cap = _dec(env.get("amount"))
        current = project_spend(
            records, scope, fleet_id=fleet_id, run_id=run_id, unit=unit, window=env.get("window")
        )
        if cap > 0 and current >= cap:
            return SpendDecision(
                verdict=DENIED,
                signal=SIGNAL_BUDGET_EXHAUSTED,
                reason=f"{scope} {unit} envelope exhausted at admission ({current} >= {cap})",
                scope=scope,
            )
    return SpendDecision(verdict=ALLOWED, signal=SIGNAL_OK, reason="admitted: all envelopes have headroom")


def admit_concurrency(active_count: int, max_concurrent_runs: Any) -> SpendDecision:
    """Admit on the concurrency dimension (semaphore ceiling, PURE).

    Over-limit yields the ``throttle`` signal (retry with backoff + honor any
    ``Retry-After``), DISTINCT from ``budget_exhausted`` (no retry). The live
    cross-process semaphore/queue/lease is a deferred seam; this is the pure ceiling
    test. ``max_concurrent_runs`` absent -> no concurrency cap.
    """
    if max_concurrent_runs is None:
        return SpendDecision(verdict=ALLOWED, signal=SIGNAL_OK, reason="no concurrency cap")
    if active_count >= int(max_concurrent_runs):
        return SpendDecision(
            verdict=DENIED,
            signal=SIGNAL_THROTTLE,
            reason=f"max_concurrent_runs reached ({active_count} >= {max_concurrent_runs}); retry with backoff",
        )
    return SpendDecision(verdict=ALLOWED, signal=SIGNAL_OK, reason="concurrency headroom available")


# ---------------------------------------------------------------------------
# Record bodies — value-free leaves the caller appends via spine.append (PURE)
# ---------------------------------------------------------------------------
def meter_record_body(
    *,
    policy_sha: str,
    run_id: str,
    recorded_at: str,
    amount: Decimal | float | int | str,
    unit: str = "$",
    fleet_id: str | None = None,
    model: str | None = None,
    window: str | None = None,
) -> dict[str, Any]:
    """Build a ``runtime_spend_ledger`` record body (no sequence/hash — the spine stamps those)."""
    body: dict[str, Any] = {
        "kind": RUNTIME_SPEND_LEDGER_RECORD_KIND,
        "record_type": RUNTIME_SPEND_LEDGER_RECORD_TYPE,
        "schema_version": "1",
        "policy_sha": policy_sha,
        "run_id": run_id,
        "recorded_at": recorded_at,
        "unit": unit,
        "amount": float(_dec(amount)),
    }
    if fleet_id is not None:
        body["fleet_id"] = fleet_id
    if model is not None:
        body["model"] = model
    if window is not None:
        body["window"] = window
    return body


def breach_record_body(
    *,
    policy_sha: str,
    run_id: str,
    recorded_at: str,
    breach_scope: str,
    breach_unit: str,
    tier: str,
    signal: str,
    limit: Decimal | float | int | str,
    observed: Decimal | float | int | str,
    decision_reason: str,
    escalation_id: str | None = None,
) -> dict[str, Any]:
    """Build a ``runtime_spend_breach`` record body (no sequence/hash — the spine stamps those)."""
    body: dict[str, Any] = {
        "kind": RUNTIME_SPEND_BREACH_RECORD_KIND,
        "record_type": RUNTIME_SPEND_BREACH_RECORD_TYPE,
        "schema_version": "1",
        "policy_sha": policy_sha,
        "run_id": run_id,
        "recorded_at": recorded_at,
        "breach_scope": breach_scope,
        "breach_unit": breach_unit,
        "tier": tier,
        "signal": signal,
        "limit": float(_dec(limit)),
        "observed": float(_dec(observed)),
        "decision_reason": decision_reason,
    }
    if escalation_id is not None:
        body["escalation_id"] = escalation_id
    return body


def spend_escalation_id(run_id: str, scope: str, unit: str, tier: str) -> str:
    """A deterministic, value-free escalation digest for a breach (PURE; NO $ amount, no clock/rng)."""
    material = "|".join((run_id, scope, unit, tier))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Circuit-breaker (Fork A) — synchronous soft/hard trip over the projection
# ---------------------------------------------------------------------------
def check_breaker(
    envelopes: Any,
    records: Any,
    *,
    run_id: str,
    fleet_id: str | None = None,
    soft_ratio: Decimal = SOFT_BREACH_RATIO,
) -> SpendDecision:
    """Return the breaker verdict for the CURRENT projection (synchronous, PURE).

    Most-restrictive-wins over the envelopes: a ``hard`` trip (ratio >= 1.0) ->
    ``escalate`` (pause + escalate, preserving state), ``budget_exhausted``; else a
    ``soft`` trip (ratio >= ``soft_ratio``) -> ``allowed`` (alert + continue); else
    clean ``allowed``. Synchronous accounting — the projection already reflects any
    just-metered leaf (async budgets lag = post-mortem, not a gate).
    """
    hard: SpendDecision | None = None
    soft: SpendDecision | None = None
    for env in sorted(_iter_envelopes(envelopes), key=lambda e: _SCOPE_ORDER.get(e.get("scope"), 9)):
        scope = str(env.get("scope"))
        unit = str(env.get("unit"))
        cap = _dec(env.get("amount"))
        if cap <= 0:
            continue
        observed = project_spend(
            records, scope, fleet_id=fleet_id, run_id=run_id, unit=unit, window=env.get("window")
        )
        ratio = observed / cap
        if ratio >= 1 and hard is None:
            hard = SpendDecision(
                verdict=ESCALATE,
                signal=SIGNAL_BUDGET_EXHAUSTED,
                reason=f"hard breach: {scope} {unit} {observed} >= cap {cap} — pause + escalate",
                scope=scope,
                tier="hard",
                escalation_id=spend_escalation_id(run_id, scope, unit, "hard"),
            )
        elif ratio >= soft_ratio and soft is None:
            soft = SpendDecision(
                verdict=ALLOWED,
                signal=SIGNAL_OK,
                reason=f"soft alert: {scope} {unit} {observed} >= {soft_ratio} of cap {cap} — continue",
                scope=scope,
                tier="soft",
            )
    if hard is not None:
        return hard
    if soft is not None:
        return soft
    return SpendDecision(verdict=ALLOWED, signal=SIGNAL_OK, reason="within envelope")


def meter_and_check(
    envelopes: Any,
    records: Any,
    cost: Decimal | float | int | str,
    *,
    policy_sha: str,
    run_id: str,
    recorded_at: str,
    unit: str = "$",
    fleet_id: str | None = None,
    model: str | None = None,
    window: str | None = None,
    soft_ratio: Decimal = SOFT_BREACH_RATIO,
) -> tuple[dict[str, Any], SpendDecision]:
    """Meter ``cost`` then synchronously check the breaker over the new projection (PURE).

    Returns ``(ledger_body, decision)``: the ``runtime_spend_ledger`` body the
    caller appends to the chain (via ``spine.append``), and the breaker verdict
    computed over ``records + the new leaf`` (synchronous — the verdict reflects the
    just-metered cost). The caller appends a ``breach_record_body`` for a soft/hard
    trip, and (for ``hard``) raises the decision to the cockpit channel (a deferred
    live seam).
    """
    body = meter_record_body(
        policy_sha=policy_sha,
        run_id=run_id,
        recorded_at=recorded_at,
        amount=cost,
        unit=unit,
        fleet_id=fleet_id,
        model=model,
        window=window,
    )
    after = list(records or []) + [body]
    decision = check_breaker(envelopes, after, run_id=run_id, fleet_id=fleet_id, soft_ratio=soft_ratio)
    return body, decision


# ---------------------------------------------------------------------------
# Composition with the G-4 control point — spend precedence before the ladder
# ---------------------------------------------------------------------------
def decide_with_spend(
    event: Any, runtime_policy: Any, *, spend_decision: SpendDecision | None = None
) -> Decision:
    """Compose the spend breaker with the G-4 ``decide()`` (PURE).

    A ``hard`` spend breach is a built-in-deny-tier verdict: it is evaluated BEFORE
    the gate-mode ladder and SURVIVES even ``full`` (YOLO) mode — a run that is out
    of budget does not proceed regardless of how permissive the action ladder is. A
    pause+escalate is the faithful disposition (state preserved), so the verdict is
    ``escalate``, never silently allowed. Absent a hard breach (no breach, or a soft
    alert that only warns), this delegates to the unmodified stateless action gate.
    """
    if spend_decision is not None and spend_decision.tier == "hard":
        return Decision(
            verdict=spend_decision.verdict,
            mode="deny",
            reason=f"spend hard-breach precedence (before gate-mode ladder): {spend_decision.reason}",
            escalation_id=spend_decision.escalation_id,
        )
    return decide(event, runtime_policy)
