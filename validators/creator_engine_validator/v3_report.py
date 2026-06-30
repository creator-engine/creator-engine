"""CE v3 — the ◆ CE Completion Report + artifact awareness (G-7.3). PURE render.

The per-run **◆ CE Completion Report** answers three plain questions over the
conserved evidence chain — *what happened · did it pass · what's next* — and
enumerates every run artifact with its inspect command. It is the heir to the
build-harness completion report, branded "CE".

Vocabulary (CANON — ``docs/architecture/stage-vocabulary.md`` §"◆ CE Completion
Report", locked 2026-06-08 / PR #165). The user-facing labels are a SKIN over the
conserved engine; this report renders, never relabels, the machine:

  * **Outcome** — the conserved ``outcome`` enum
    (``runtime_evidence_spine.RUN_OUTCOMES`` / ``schemas/runtime-evidence.schema.yaml``),
    rendered PLAINLY: ``pr_opened``→"PR opened", ``pr_merged``→"Merged",
    ``review_submitted``→"Review submitted", ``research_delivered``→"Research
    delivered", ``no_change``→"No change needed".
  * **Verdict** (was "determination") — the grading synthesis (Done-when met · CI ·
    in-scope · spend of Budget); "Verdict" reinforces that the grader lives
    outside the agent.
  * **Next** (was "next step") — derived from Outcome × Change-type.
  * **Artifacts** / **Inspect** — the artifact enumeration + the ``ce``/``gh``
    inspect commands (``ce`` is the user-facing command; see ``v3_cli.CE_CMD``).

It inherits the other two vocabularies: ``acceptance_criteria``→**Done-when**,
``mutation_class``→**Change-type**, the spend cap→**Budget**, manifest-fidelity→
**"in scope ✓"**.

Boundary (CI-pure): pure rendering over a run-summary (``dict``).
``summary_from_evidence`` folds the REAL conserved signals from an evidence chain
— the typed run-outcome record (``RUN_OUTCOME_RECORD_TYPE``) and the G-5 spend
projection (``runner.spend_gate.project_spend``). The live assembly of the full
grading synthesis from a running run is the named DEFERRED seam — the
G-4/G-5/G-6 cut.

PURE: no disk / subprocess / socket / clock / rng. Defensive only — it makes CE's
own run evidence legible; never an offensive capability.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .runner.spend_gate import project_spend
from .runtime_evidence_spine import RUN_OUTCOMES, RUN_OUTCOME_RECORD_TYPE

_BRAND = "◆ CE"

#: The USER-FACING command name (Operator-ratified directive) the inspect commands
#: speak — the pilot installs v3-only and the installer exposes the CLI as ``ce``
#: (the internal monorepo console_script is ``cev3``; never shown to users).
CE_CMD = "ce"

#: The canon plain renderings of the conserved ``outcome`` enum (the skin). Keys
#: MUST stay set-equal to ``RUN_OUTCOMES`` (guarded by a test).
OUTCOME_LABELS = {
    "pr_opened": "PR opened",
    "pr_merged": "Merged",
    "review_submitted": "Review submitted",
    "research_delivered": "Research delivered",
    "no_change": "No change needed",
}


# ---------------------------------------------------------------------------
# Field renderers (PURE)
# ---------------------------------------------------------------------------
def outcome_label(outcome: Any) -> str:
    """Render the conserved ``outcome`` enum plainly (the canon skin)."""
    if not outcome:
        return "—"
    return OUTCOME_LABELS.get(outcome, str(outcome))


def _fmt_amount(amount: Any) -> str:
    d = Decimal(str(amount)).normalize()
    return f"{d:f}"


def _money(amount: Any, unit: str) -> str:
    """Render an amount with its unit: ``$`` prefixes, ``%`` (or other) suffixes."""
    a = _fmt_amount(amount)
    return f"${a}" if unit == "$" else f"{a}{unit}"


def _spend_segment(summary: dict[str, Any]) -> str | None:
    """'14% of Budget S' — spend rendered against the run Budget (the cap)."""
    spent, budget = summary.get("spent"), summary.get("budget")
    if budget is None or spent is None:
        return None
    cap = Decimal(str(budget))
    if cap <= 0:
        return None
    pct = (Decimal(str(spent)) / cap) * 100
    size = summary.get("budget_size")  # the appetite size label (e.g. "S"), if known
    of = f"Budget {size}" if size else _money(cap, summary.get("unit", "$"))
    return f"{pct:.0f}% of {of}"


def render_verdict(summary: dict[str, Any]) -> str:
    """The grading synthesis line (Done-when · CI · in-scope · spend) — the grade."""
    parts: list[str] = []
    total = summary.get("done_when_total")
    if total is not None:
        parts.append(f"Done-when {summary.get('done_when_met', 0)}/{total} met")
    ci = summary.get("ci")
    if ci:
        parts.append("tests green" if ci == "green" else f"tests {ci}")
    in_scope = summary.get("in_scope")
    if in_scope is not None:
        parts.append("in scope ✓" if in_scope else "out of scope ✗")
    spend = _spend_segment(summary)
    if spend:
        parts.append(spend)
    return " · ".join(parts) if parts else "—"


def render_next(summary: dict[str, Any]) -> str:
    """The derived next step (Outcome × Change-type) — the canon **Next**."""
    outcome = summary.get("outcome")
    change = summary.get("change_type")
    pr = summary.get("pr")
    if outcome == "pr_opened":
        approval = f"  (Change-type {change} → your approval)" if change else ""
        return f"→ Review PR #{pr}{approval}" if pr else "→ Review the change"
    if outcome == "pr_merged":
        return "→ Done — merged"
    if outcome == "review_submitted":
        return "→ Address the review"
    if outcome == "research_delivered":
        return "→ Read the delivered research"
    if outcome == "no_change":
        return "→ Nothing to ship — no change needed"
    return "—"


# ---------------------------------------------------------------------------
# Artifact awareness (PURE)
# ---------------------------------------------------------------------------
def enumerate_artifacts(summary: dict[str, Any]) -> list[dict[str, str]]:
    """Enumerate the run's artifacts with their inspect commands (the canon skin)."""
    run = summary.get("run_id")
    scope = summary.get("scope_id")
    pr = summary.get("pr")
    out: list[dict[str, str]] = []
    if pr:
        out.append({"kind": "pr", "label": f"PR #{pr}", "inspect": f"gh pr view {pr}"})
    if scope:
        out.append({"kind": "scope", "label": f"Scope {scope}", "inspect": f"{CE_CMD} show {scope}"})
    for extra in summary.get("artifacts") or []:
        if isinstance(extra, dict) and extra.get("label"):
            out.append(extra)
    if run and scope:
        inspect = f"{CE_CMD} artifacts {scope} --run-id {run}"
        out.append({"kind": "evidence", "label": "evidence-chain ✓", "inspect": inspect})
        if summary.get("spent") is not None:
            out.append({"kind": "spend", "label": "spend", "inspect": inspect})
    return out


# ---------------------------------------------------------------------------
# The ◆ CE Completion Report block (PURE)
# ---------------------------------------------------------------------------
def render_report(summary: dict[str, Any]) -> list[str]:
    """Render the per-run ◆ CE Completion Report (Outcome · Verdict · Next + Artifacts)."""
    run = summary.get("run_id", "—")
    scope = summary.get("scope_id", "—")
    outcome_line = f"│ Outcome   {outcome_label(summary.get('outcome'))}"
    if summary.get("pr"):
        outcome_line += f" → #{summary['pr']}"
    lines = [
        f"┌─ {_BRAND} COMPLETION REPORT · run {run} · Scope {scope} " + "─" * 18,
        outcome_line,
        f"│ Verdict   {render_verdict(summary)}",
        f"│ Next      {render_next(summary)}",
    ]
    arts = enumerate_artifacts(summary)
    if arts:
        lines.append("│ Artifacts " + " · ".join(a["label"] for a in arts))
        inspects = list(dict.fromkeys(a["inspect"] for a in arts if a.get("inspect")))
        lines.append("│ Inspect   " + "   |   ".join(inspects))
    lines.append("└" + "─" * 60)
    return lines


# ---------------------------------------------------------------------------
# Fold the REAL conserved signals from an evidence chain (PURE)
# ---------------------------------------------------------------------------
def summary_from_evidence(
    records: Any,
    *,
    scope_id: str | None = None,
    run_id: str | None = None,
    budget: Any = None,
    unit: str = "$",
    **grading: Any,
) -> dict[str, Any]:
    """Build a run-summary by folding the REAL run-outcome + spend off a chain.

    Reads the conserved typed run-outcome record (``RUN_OUTCOME_RECORD_TYPE`` —
    the terminal disposition + its value-free ``change_set`` PR ref) and the G-5
    spend projection (``project_spend``). The grading synthesis (Done-when / CI /
    in-scope) is injected via ``**grading`` — its live assembly is the deferred
    seam. Pure.
    """
    outcome: Any = None
    pr: Any = None
    for r in records or []:
        if not isinstance(r, dict):
            continue
        if r.get("record_type") == RUN_OUTCOME_RECORD_TYPE:
            outcome = r.get("outcome", outcome)
            run_id = run_id or r.get("run_id")
            cs = r.get("change_set") or {}
            # ``pr_number`` is the conserved change_set field (runtime-evidence schema);
            # ``pr`` is a lenient fallback only.
            pr = cs.get("pr_number") or cs.get("pr") or pr
    spent = project_spend(records, "run", unit=unit, run_id=run_id) if budget is not None else None
    summary: dict[str, Any] = {
        "scope_id": scope_id, "run_id": run_id, "outcome": outcome, "pr": pr,
        "spent": spent, "budget": budget, "unit": unit,
    }
    summary.update(grading)
    return summary
