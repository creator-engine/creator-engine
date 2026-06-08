"""CE v3 session frame + the unified resource status line (G-7.1). PURE render.

The branded "your agent, under CE" frame: a launch banner + a persistent status
line that fuses three signals into ONE session resource/health surface —
  (a) the canon STAGE skin (Frame → Shape → Build → Review → Ship, with counts)
      over the conserved board/spec-lifecycle states (reused from ``coordination``
      — never a third vocabulary);
  (b) the CONTEXT-window meter (GH #157); and
  (c) the SPEND meter (the G-5 ``runner.spend_gate.project_spend`` projection) —
with **boundary-aware** checkpoint / ``/clear`` nudges.

#157 constraint — **PROJECT-LEVEL / CE-NATIVE.** A governed CE seat launches with
``--setting-sources project``, which excludes the user ``~/.claude`` settings, so a
user-level ``statusLine`` is never loaded by a governed seat. This surface is
therefore CE-native and project-scoped (it lives with the v3 CLI, not in user
settings). It **CONSUMES the harness's authoritative**
``context_window.used_percentage`` — it never recomputes the token count (the
assistant historically guesses high; the harness number is the only authority).

Boundary (CI-pure; the LIVE seam is DEFERRED): this module is the pure render +
threshold + nudge logic, fed ``(context_pct, spend projection)``. The live
``statusLine``-command tap into a running TUI session (reading the harness number
each turn) is the deferred live seam — exactly as G-4/G-5/G-6 deferred their live
taps. The spend meter folds the REAL G-5 projection over an evidence spine.

PURE: no disk / subprocess / socket / clock / rng. Defensive only.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from . import coordination
from .runner.spend_gate import SOFT_BREACH_RATIO, project_spend

#: Context-window nudge thresholds (% of the window). Sourced from GH #157's
#: prototype (warn ≥ 45 / urgent ≥ 60) — the boundary at which a long batch-strict
#: arc should checkpoint and consider ``/clear`` before silent exhaustion.
CONTEXT_WARN_PCT = 45.0
CONTEXT_URGENT_PCT = 60.0

#: Spend tiers reuse the G-5 circuit-breaker ratios verbatim (single source of
#: truth): soft alert at ``SOFT_BREACH_RATIO`` (~0.8), hard at the cap (1.0).
SPEND_SOFT_RATIO = SOFT_BREACH_RATIO  # Decimal("0.8")

_BRAND = "◆ CE"


# ---------------------------------------------------------------------------
# Meters (PURE) — each maps a raw signal to a {value, state} the line renders
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ContextMeter:
    """The context-window meter: the harness's % + a threshold state."""

    pct: float | None
    state: str  # "ok" | "warn" | "urgent" | "unknown"


@dataclass(frozen=True)
class SpendMeter:
    """The spend meter: the G-5 projected spend vs the run cap + a breaker state."""

    spent: Decimal | None
    cap: Decimal | None
    unit: str
    ratio: float | None
    state: str  # "ok" | "soft" | "hard" | "unmetered"


def context_meter(pct: Any) -> ContextMeter:
    """Map the harness context-% to a threshold state (CONSUMED, never recomputed)."""
    if pct is None:
        return ContextMeter(None, "unknown")
    p = float(pct)
    if p >= CONTEXT_URGENT_PCT:
        state = "urgent"
    elif p >= CONTEXT_WARN_PCT:
        state = "warn"
    else:
        state = "ok"
    return ContextMeter(p, state)


def spend_meter(spent: Any, cap: Any, unit: str = "$") -> SpendMeter:
    """Map projected spend vs cap to a breaker state (reuses the G-5 ratios)."""
    if cap is None:
        return SpendMeter(
            None if spent is None else Decimal(str(spent)), None, unit, None, "unmetered"
        )
    spent_d = Decimal(str(spent or 0))
    cap_d = Decimal(str(cap))
    if cap_d <= 0:
        return SpendMeter(spent_d, cap_d, unit, None, "unmetered")
    ratio = spent_d / cap_d
    if ratio >= 1:
        state = "hard"
    elif ratio >= SPEND_SOFT_RATIO:
        state = "soft"
    else:
        state = "ok"
    return SpendMeter(spent_d, cap_d, unit, float(ratio), state)


def spend_meter_from_spine(
    records: Any, cap: Any, *, scope: str = "run", unit: str = "$", run_id: str | None = None
) -> SpendMeter:
    """Fold the REAL G-5 spend projection over an evidence spine, then meter it."""
    spent = project_spend(records, scope, unit=unit, run_id=run_id)
    return spend_meter(spent, cap, unit)


# ---------------------------------------------------------------------------
# Render (PURE) — the banner, the unified status line, and the nudges
# ---------------------------------------------------------------------------
_CTX_MARK = {"ok": "", "warn": " ⚠", "urgent": " ⛔", "unknown": ""}
_SPEND_MARK = {"ok": "", "soft": " ⚠", "hard": " ⛔", "unmetered": ""}


def fmt_amount(amount: Decimal | None) -> str:
    """Render a spend amount cleanly (drop trailing zeros: 5.0→5, 3.50→3.5)."""
    if amount is None:
        return "—"
    d = Decimal(amount).normalize()
    # normalize() can yield exponent form (1E+2); force plain fixed-point.
    return f"{d:f}"


def render_banner(*, repo: str = "—", transport: str = "—", backend: str = "—", root: str = ".ce/state") -> str:
    """The ``cev3 session`` launch banner — always-on "your agent, under CE"."""
    return (
        f"◆ Creator Engine · governed session · repo {repo} · "
        f"transport {transport} · backend {backend} · state {root}"
    )


def _ctx_segment(c: ContextMeter) -> str:
    if c.pct is None:
        return "ctx —"
    return f"ctx {c.pct:.0f}%{_CTX_MARK[c.state]}"


def _spend_segment(s: SpendMeter) -> str:
    if s.state == "unmetered" or s.cap is None:
        return "spend —"
    pct = f"{s.ratio * 100:.0f}%" if s.ratio is not None else "—"
    return f"spend {s.unit}{fmt_amount(s.spent)}/{s.unit}{fmt_amount(s.cap)} {pct}{_SPEND_MARK[s.state]}"


def render_status_line(phase_counts: dict[str, int], context: ContextMeter, spend: SpendMeter) -> str:
    """The ONE unified resource/health line: stage skin │ context │ spend."""
    stage = " · ".join(f"{p} {phase_counts.get(p, 0)}" for p in coordination.COGNITIVE_PHASES)
    return f"{_BRAND} · {stage}  │  {_ctx_segment(context)}  │  {_spend_segment(spend)}"


def nudges(context: ContextMeter, spend: SpendMeter, *, at_boundary: bool) -> list[str]:
    """Boundary-aware checkpoint/escalate nudges (empty mid-output by design).

    The context checkpoint/``/clear`` nudge fires only ``at_boundary`` (a turn /
    batch boundary — never mid-output, which would tax the user). The spend hard
    breach always surfaces (it is a governance event), the soft alert at boundary.
    """
    out: list[str] = []
    if at_boundary and context.state in ("warn", "urgent"):
        verb = "checkpoint now and consider `/clear`" if context.state == "urgent" else "consider checkpointing soon"
        out.append(f"{_BRAND} · context {context.pct:.0f}% — {verb} (save resume state first)")
    if spend.state == "hard":
        out.append(
            f"{_BRAND} · spend cap reached "
            f"({spend.unit}{fmt_amount(spend.spent)}/{spend.unit}{fmt_amount(spend.cap)}) — pause + escalate"
        )
    elif spend.state == "soft" and at_boundary:
        out.append(f"{_BRAND} · spend at {spend.ratio * 100:.0f}% of cap — alert (continue)")
    return out


def render_session(
    phase_counts: dict[str, int],
    *,
    context: ContextMeter | None = None,
    spend: SpendMeter | None = None,
    at_boundary: bool = True,
    repo: str = "—",
    transport: str = "—",
    backend: str = "—",
    root: str = ".ce/state",
) -> list[str]:
    """Assemble the full frame: banner + the unified status line + any nudges."""
    context = context or ContextMeter(None, "unknown")
    spend = spend or SpendMeter(None, None, "$", None, "unmetered")
    return [
        render_banner(repo=repo, transport=transport, backend=backend, root=root),
        render_status_line(phase_counts, context, spend),
        *nudges(context, spend, at_boundary=at_boundary),
    ]
