"""CE v3 shaping dialogue — the Frame→Shape grill-me engine + the chat→Scope dial.

How a developer's free-form chat becomes a **Scope** (a tracked, ratifiable bet)
and how CE shapes it (the UX of the **Frame** and **Shape** stages). PURE.

The principle (``docs/architecture/shaping-ux.md``): **the agent drafts, an
external rubric grades, the human ratifies.** Every shaping locus is the same
move — the agent DRAFTS a proposal → checks it against an EXTERNAL rubric of
"what must be present and valid here" → FLAGS the gaps → asks the MINIMUM
questions to close them → the human supplies the **human-only** fields and
ratifies. This is "the grader lives outside the agent" at the dialogue layer.

**One grill-me engine, per-locus rubrics — and the rubrics are existing CE
checks.** The Scope-shaping rubric IS the Definition-of-Ready predicate
(``coordination.scope_is_ready``); the engine reuses governance rather than
re-deriving "ready." This module supplies the *Scope-shaping* locus.

Two field-derivation rules (``shaping-ux.md``):
  * **Budget (`appetite`) is human-only.** The agent drafts every field EXCEPT
    the budget — the fixed bet is the human's to place.
  * **Change-type (`mutation_class`) is safe-by-default.** The agent PROPOSES the
    risk tier; the human may **tighten it for free** (raise the blast-radius
    class → more gating); **loosening requires ratification** (the agent can
    never unilaterally enlarge the permitted blast radius).

The chat→Scope **detect-and-offer** dial (E3): chat stays free (Frame); when CE
detects a concrete mutation intent it drafts the Scope inline and asks ONE cheap,
inline, cancel-safe confirm (never a blocking modal) — nothing is tracked until
that yes (the confirm IS the Frame→Shape gate). Eagerness =
``f(persona, risk-class)``: the persona sets the baseline bar, the Scope's
``mutation_class`` modulates it, both tightening as blast radius rises. Bias
conservative when uncertain. The thresholds here are a **conservative default**;
the live telemetry-tune loop (instrument offer→accept/decline and adapt) is the
named DEFERRED seam — exactly the G-4/G-5/G-6 cut.

PURE: no disk / subprocess / socket / clock / rng. Defensive only — governs CE's
own work intake; never an offensive capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field as _field
import re
from typing import Any

from . import coordination

#: Fields the agent NEVER drafts — the human's to supply (the bet's budget).
HUMAN_ONLY_FIELDS = frozenset({"appetite"})

#: The user-facing Scope-card labels (the canon skin) over the conserved fields.
CARD_LABELS = {
    "intent": "Goal",
    "acceptance_criteria": "Done-when",
    "appetite": "Budget",
    "mutation_class": "Change-type",
}

#: The conserved mutation-class taxonomy ordered by BLAST RADIUS (low→high). The
#: re-tier rule keys off this order; the canon listing in stage-vocabulary.md.
MUTATION_RISK_ORDER = (
    "none", "docs", "code", "schema", "deploy",
    "governance", "identity", "security", "attestation", "redaction",
)

#: Low-blast-radius classes — the dial may offer more readily for these. Anything
#: NOT explicitly known-low (incl. an unknown/absent class) falls to the HIGH band
#: — "bias conservative when uncertain" (shaping-ux.md).
_LOW_RISK = frozenset({"none", "docs", "code"})

#: The minimum question per gap field (the engine asks only what it must).
_GAP_QUESTION = {
    "intent": "What are you trying to do? (the Goal)",
    "acceptance_criteria": "What does done look like — the testable checks? (Done-when)",
    "appetite": "How much are you willing to spend — a fixed cap, not an estimate? (Budget — your call)",
    "mutation_class": "What kind of change is this, and how risky? (Change-type)",
}


# ---------------------------------------------------------------------------
# The grill-me engine — draft → rubric → gaps → minimum questions (PURE)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Gap:
    """A missing/invalid Scope field the dialogue must close before Ready."""

    field: str        # the conserved schema field
    label: str        # the user-facing Scope-card label
    question: str     # the minimum question to close it
    human_only: bool  # True ⇒ only the human may supply it (the budget)


@dataclass(frozen=True)
class ShapingResult:
    """The grill-me outcome: the gaps, the minimum questions, and the card."""

    ready: bool
    gaps: tuple[Gap, ...]
    card: str

    @property
    def questions(self) -> tuple[str, ...]:
        return tuple(g.question for g in self.gaps)

    @property
    def human_only_gaps(self) -> tuple[Gap, ...]:
        return tuple(g for g in self.gaps if g.human_only)


@dataclass(frozen=True)
class PrdScopeSeed:
    """A bounded-first Scope draft seeded from an existing requirements doc."""

    source_path: str
    source_note: str
    candidate_slice: str
    draft: dict[str, Any] = _field(default_factory=dict)


def _gap_for(field: str) -> Gap:
    return Gap(field, CARD_LABELS[field], _GAP_QUESTION[field], field in HUMAN_ONLY_FIELDS)


def shape(draft: Any) -> ShapingResult:
    """Run the Scope-shaping grill-me over a draft (PURE).

    The rubric IS ``coordination.scope_is_ready`` (the DoR predicate) — the engine
    does not re-derive "ready." Returns the gaps (each with its user-facing label,
    the minimum question, and whether it is human-only), and the rendered card.
    """
    ready, _reasons = coordination.scope_is_ready(draft)
    draft = draft if isinstance(draft, dict) else {}
    gaps: list[Gap] = []
    if not draft.get("intent"):
        gaps.append(_gap_for("intent"))
    ac = draft.get("acceptance_criteria")
    if not isinstance(ac, list) or not ac:
        gaps.append(_gap_for("acceptance_criteria"))
    if coordination._appetite_reasons(draft.get("appetite")):
        gaps.append(_gap_for("appetite"))
    if draft.get("mutation_class") not in coordination.MUTATION_CLASSES:
        gaps.append(_gap_for("mutation_class"))
    return ShapingResult(ready=ready, gaps=tuple(gaps), card=render_card(draft, tuple(gaps)))


def render_card(draft: Any, gaps: tuple[Gap, ...] = ()) -> str:
    """Render the gap-aware Scope card in the canon vocabulary (the skin)."""
    draft = draft if isinstance(draft, dict) else {}
    missing = {g.field for g in gaps}
    phase = coordination.cognitive_phase(coordination.project_scope_state(draft)["state"])
    ac = draft.get("acceptance_criteria") or []
    appetite = draft.get("appetite") or {}
    budget = f"{appetite.get('amount')}{appetite.get('unit')}" if "appetite" not in missing and appetite else "?"
    goal = "✓" if "intent" not in missing else "?"
    change = draft.get("mutation_class") if "mutation_class" not in missing else "?"
    ready_mark = "✓" if (not gaps and coordination.is_ratified(draft)) else ("○" if not gaps else "?")
    sid = draft.get("scope_id", "draft")
    return (
        f"◆ CE · {phase} → {sid!r}  "
        f"(Goal {goal} · Done-when {len(ac)} · Budget {budget} · "
        f"Change-type {change} · Ready {ready_mark})"
    )


# ---------------------------------------------------------------------------
# Field-derivation rule: Change-type is safe-by-default (PURE)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RetierResult:
    allowed: bool
    mutation_class: str   # the resulting class (unchanged on refusal)
    direction: str        # "tighten" | "loosen" | "same"
    reason: str


def _risk_rank(mutation_class: Any) -> int:
    try:
        return MUTATION_RISK_ORDER.index(mutation_class)
    except ValueError:
        return -1


def retier(proposed: str, requested: str, *, ratified: bool = False) -> RetierResult:
    """Apply the safe-by-default change-type rule (PURE).

    Tightening (requesting a HIGHER blast-radius class → more gating) is **free**.
    Loosening (a LOWER class → less gating) is allowed **only with ratification**
    — the agent can never unilaterally enlarge the permitted blast radius.
    """
    pr, rr = _risk_rank(proposed), _risk_rank(requested)
    if rr < 0:
        return RetierResult(False, proposed, "same", f"unknown change-type {requested!r}")
    if rr > pr:
        return RetierResult(True, requested, "tighten", "tightened to a higher-risk tier (free)")
    if rr == pr:
        return RetierResult(True, requested, "same", "no change")
    if ratified:
        return RetierResult(True, requested, "loosen", "loosened with ratification")
    return RetierResult(
        False, proposed, "loosen",
        "loosening the change-type lowers gating — requires ratification (safe-by-default)",
    )


def agent_may_draft(field: str) -> bool:
    """True iff the agent may draft this field (everything except the budget)."""
    return field not in HUMAN_ONLY_FIELDS


# ---------------------------------------------------------------------------
# PRD context injection — seed one draft, then reuse the grill-me engine (PURE)
# ---------------------------------------------------------------------------
_GENERIC_PRD_HEADINGS = frozenset({
    "prd",
    "product requirements document",
    "requirements",
    "overview",
    "background",
    "context",
    "goals",
    "goal",
    "non-goals",
    "non goals",
    "scope",
})


def _clean_candidate(text: str) -> str:
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s*", "", text)
    text = re.sub(r"^\s*(?:feature|slice|story|requirement)\s*[:：-]\s*", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" \t\"'`.:")
    return text


def _slugify_scope_id(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if not slug or not slug[0].isalpha():
        slug = f"scope-{slug}" if slug else "scope-from-prd"
    if len(slug) < 3:
        slug = f"{slug}-scope"
    return slug[:64].rstrip("-")


def _first_candidate_slice(text: str) -> str:
    lines = text.splitlines()
    for raw in lines:
        stripped = raw.strip()
        if not stripped.startswith("#"):
            continue
        candidate = _clean_candidate(stripped)
        lowered = candidate.lower()
        if candidate and lowered not in _GENERIC_PRD_HEADINGS and "prd" not in lowered:
            return candidate

    for raw in lines:
        candidate = _clean_candidate(raw)
        if not candidate:
            continue
        lowered = candidate.lower()
        if any(word in lowered for word in (" flow", " feature", " slice", " story", " requirement")):
            return candidate

    for raw in lines:
        candidate = _clean_candidate(raw)
        if candidate and candidate.lower() not in _GENERIC_PRD_HEADINGS:
            return candidate
    return "first PRD slice"


def _acceptance_criteria_from_prd(text: str, *, limit: int = 5) -> tuple[str, ...]:
    lines = text.splitlines()
    in_acceptance = False
    out: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        heading_text = _clean_candidate(stripped).lower()
        if stripped.startswith("#"):
            if in_acceptance:
                break
            in_acceptance = heading_text in {"acceptance criteria", "done when", "done-when"}
            continue
        if not in_acceptance:
            continue
        candidate = _clean_candidate(stripped)
        if candidate:
            out.append(candidate)
        if len(out) >= limit:
            break
    return tuple(out)


def _change_type_from_prd(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("documentation", "docs", "copy-only", "copy only")):
        return "docs"
    return "code"


def seed_scope_from_prd(text: str, source_path: str) -> PrdScopeSeed:
    """Return one bounded Scope draft seeded by PRD context (PURE).

    The PRD informs the draft; it does not authorize work. This helper performs
    only the context-injection step. Callers still run :func:`shape` over the
    returned draft so the same grill-me rubric owns readiness and gap questions.
    """
    candidate = _first_candidate_slice(text)
    draft: dict[str, Any] = {
        "scope_id": _slugify_scope_id(candidate),
        "intent": f"Implement {candidate} as described in {source_path}",
        "mutation_class": _change_type_from_prd(text),
    }
    acceptance_criteria = _acceptance_criteria_from_prd(text)
    if acceptance_criteria:
        draft["acceptance_criteria"] = list(acceptance_criteria)
    return PrdScopeSeed(
        source_path=source_path,
        source_note=f"Source PRD: {source_path}",
        candidate_slice=candidate,
        draft=draft,
    )


# ---------------------------------------------------------------------------
# The chat→Scope detect-and-offer dial — f(persona, risk-class) (PURE)
# ---------------------------------------------------------------------------
#: Intent-to-act signal strengths (weak→strong).
SIGNAL_ORDER = ("vague", "actionable", "clear", "explicit")
_SIGNAL_RANK = {s: i for i, s in enumerate(SIGNAL_ORDER)}

#: The conservative default eagerness table (the live tune-loop is deferred).
#: Each cell is the MINIMUM signal that triggers the inline offer.
_OFFER_THRESHOLD = {
    ("dev", "low"): "clear",        # Dev: offer on a fairly clear signal
    ("dev", "high"): "explicit",    # Dev + high risk: only an explicit signal-to-act
    ("ceo", "low"): "actionable",   # CEO: offer eagerly on any actionable intent
    ("ceo", "high"): "clear",       # CEO + high risk: still tightens (confirm-heavier)
}


def risk_class(mutation_class: Any) -> str:
    """Collapse the mutation_class to the dial's low/high risk band.

    Only the explicitly known-low classes are "low"; everything else — including
    an unknown or absent class — is "high" (bias conservative when uncertain).
    """
    return "low" if mutation_class in _LOW_RISK else "high"


def offer_threshold(persona: Any, mutation_class: Any) -> str:
    """The minimum intent signal that triggers an offer (conservative default).

    Bias conservative when uncertain: an unknown persona/cell falls back to the
    strictest threshold (``explicit``).
    """
    key = (str(persona).lower(), risk_class(mutation_class))
    return _OFFER_THRESHOLD.get(key, "explicit")


def should_offer(persona: Any, mutation_class: Any, signal: Any) -> bool:
    """Decide whether to surface the inline chat→Scope offer (PURE).

    The offer is a cheap, inline, cancel-safe keystroke — never a blocking modal;
    this only decides WHETHER it fires. Returns True iff the detected intent
    ``signal`` meets the ``f(persona, risk-class)`` threshold. Unknown signals are
    treated as the weakest (no offer) — bias conservative.
    """
    needed = offer_threshold(persona, mutation_class)
    return _SIGNAL_RANK.get(str(signal).lower(), 0) >= _SIGNAL_RANK[needed]
