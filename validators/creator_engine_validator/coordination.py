"""CE v3 coordination layer (the OUTER loop) — the Scope dispatch spine. PURE.

The coordination hierarchy's pure substrate: the **Scope** is the ephemeral
atomic unit of work (a ratifiable, scope-boxed task with testable acceptance
criteria + a Shape-Up appetite + an isolated execution). A ratified, DoR-valid
Scope dispatches ONE isolated run governed by the agent-interaction contract
(G-4) and the tokenomics gate (G-5). This module is the seam where the outer
loop meets the inner per-run governance.

Stage vocabulary (CANON — ``docs/architecture/stage-vocabulary.md``): the Scope's
mechanical ``state`` is the CONSERVED spec-lifecycle
(``draft → ready → in_progress → verified → ratified → done`` — conserved
verbatim, zero new enums). The user-facing cognitive phase
(``Frame → Shape → Build → Review → Ship``) is a PRESENTATION SKIN derived from
``state`` via the canon dual-mapping. This module never invents a third
vocabulary: it conserves the machine and projects the skin over it.

The gate chain (design — two ends, risk-tiered):
  * **Front (Shape→Build):** a Scope cannot dispatch until ``intent +
    acceptance_criteria + appetite + mutation_class`` are present & valid
    (Definition-of-Ready) AND a ratifier has placed the bet
    (``ratification``). ``assemble_dispatch`` REFUSES otherwise.
  * **Middle (Build/Review):** ``execution`` is governed per-action by G-4
    (``runner.audit_overlay.decide``), metered by G-5
    (``runner.spend_gate``), and graded by CI.
  * **Back (Ship):** the ``mutation_class``-tiered ``human_ratification_required``
    ratified-merge + branch-protection review (existing machinery; the Scope's
    ``mutation_class`` drives it).

**PURE.** Every function here is pure — no disk, subprocess, socket, wall-clock,
or rng. The cumulative state is a PROJECTION over committed signals (Scopes are
committed artifacts; ``state`` is derived, never a hand-set FSM). The LIVE
dispatch (actually spawning a run via ``run_assembly.make_run_driver`` /
``orchestrator.run_plan``) is a deferred seam; ``assemble_dispatch`` produces the
run INPUTS. The durable Skill axis + the finding-schema/discard-on-drift gate are
deferred.

Defensive only — it governs CE's own work intake; never an offensive capability.

See:
  - ``docs/contracts/scope.md``
  - ``docs/architecture/stage-vocabulary.md`` (the dual-mapping canon)
  - ``schemas/scope.schema.yaml``
  - ``runner/spend_gate.py`` (the appetite→cap join target) / ``runner/audit_overlay.py`` (G-4)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

#: The CONSERVED mechanical spec-lifecycle (verbatim from the stage-vocabulary
#: canon / ``schemas/spec-wrapper-sidecar.schema.yaml``). Source of truth.
SPEC_LIFECYCLE = ("draft", "ready", "in_progress", "verified", "ratified", "done")

#: "Ready or later" — the states past the DoR + bet front gate (mirrors
#: ``checks.definition_of_ready.READY_OR_LATER``). DoR completeness + the bet are
#: REQUIRED for these states.
READY_OR_LATER = frozenset({"ready", "in_progress", "verified", "ratified", "done"})

#: The user-facing cognitive phases (the canon presentation skin).
COGNITIVE_PHASES = ("Frame", "Shape", "Build", "Review", "Ship")

#: The canon dual-mapping: mechanical spec-lifecycle state → cognitive phase.
#: (Frame=draft · Shape=ready · Build=in_progress · Review=verified ·
#: Ship=ratified→done.) Single-valued projection — the dominant phase per state.
PHASE_BY_STATE = {
    "draft": "Frame",
    "ready": "Shape",
    "in_progress": "Build",
    "verified": "Review",
    "ratified": "Ship",
    "done": "Ship",
}

#: The canon board label per state (BACKLOG/SHAPE→READY/RUN/REVIEW/MERGE).
BOARD_BY_STATE = {
    "draft": "BACKLOG",
    "ready": "READY",
    "in_progress": "RUN",
    "verified": "REVIEW",
    "ratified": "MERGE",
    "done": "MERGE",
}

#: The shared mutation-class taxonomy (risk tier) + ``none``.
MUTATION_CLASSES = frozenset(
    {"docs", "code", "schema", "deploy", "governance", "identity", "security",
     "attestation", "redaction", "none"}
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SPEND_UNITS = ("$", "%")


# ---------------------------------------------------------------------------
# The canon skin — derive the cognitive phase from the mechanical state (PURE)
# ---------------------------------------------------------------------------
def cognitive_phase(state: Any) -> str:
    """Return the canon cognitive phase (Frame/Shape/Build/Review/Ship) for a state.

    A pure projection over the CONSERVED spec-lifecycle per the dual-mapping —
    never a stored third vocabulary. An absent state ⇒ ``draft`` ⇒ ``Frame``.
    """
    return PHASE_BY_STATE.get(state if state else "draft", "Frame")


def board_label(state: Any) -> str:
    """Return the canon board label (BACKLOG/READY/RUN/REVIEW/MERGE) for a state."""
    return BOARD_BY_STATE.get(state if state else "draft", "BACKLOG")


# ---------------------------------------------------------------------------
# Definition-of-Ready front gate (PURE)
# ---------------------------------------------------------------------------
def _appetite_reasons(appetite: Any) -> list[str]:
    """Return reasons an appetite is not a valid, derivable budget (empty = ok)."""
    if not isinstance(appetite, dict):
        return ["appetite must be an object {amount, unit}"]
    reasons: list[str] = []
    amount = appetite.get("amount")
    if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
        reasons.append("appetite.amount must be a number > 0")
    if appetite.get("unit") not in _SPEND_UNITS:
        reasons.append("appetite.unit must be '$' or '%'")
    return reasons


def scope_is_ready(scope: Any) -> tuple[bool, list[str]]:
    """The DoR predicate (PURE): is the Scope ready to dispatch?

    Requires ``intent`` + non-empty ``acceptance_criteria`` + a valid, derivable
    ``appetite`` + a valid ``mutation_class``. Returns ``(ok, reasons)``; the
    reasons name what is missing/invalid (the front-gate "spec quality" check).
    """
    reasons: list[str] = []
    if not (isinstance(scope, dict)):
        return False, ["scope must be a mapping"]
    if not scope.get("intent"):
        reasons.append("intent is required")
    ac = scope.get("acceptance_criteria")
    if not isinstance(ac, list) or not ac:
        reasons.append("acceptance_criteria must be a non-empty list")
    reasons.extend(_appetite_reasons(scope.get("appetite")))
    if scope.get("mutation_class") not in MUTATION_CLASSES:
        reasons.append("mutation_class must be a valid taxonomy member")
    return (not reasons), reasons


def is_ratified(scope: Any) -> bool:
    """True when the Scope carries a valid value-free bet ratification (PURE)."""
    if not isinstance(scope, dict):
        return False
    rat = scope.get("ratification")
    return (
        isinstance(rat, dict)
        and isinstance(rat.get("approver_ref"), str)
        and bool(_HEX64_RE.match(rat["approver_ref"]))
        and isinstance(rat.get("ratified_scope_sha"), str)
        and bool(_HEX64_RE.match(rat["ratified_scope_sha"]))
    )


# ---------------------------------------------------------------------------
# The appetite → tokenomics-cap join (the explicit G-5 link, PURE)
# ---------------------------------------------------------------------------
def appetite_to_spend_envelope(appetite: dict[str, Any]) -> dict[str, Any]:
    """Derive a ``run``-scope ``spend_envelope`` from a Scope's appetite (PURE).

    The clean join between Shape-Up planning and the G-5 tokenomics gate: a
    fixed-budget appetite ``{amount, unit, window?}`` becomes a ``run``-scope
    ``spend_envelope`` the G-5 ``spend_gate.admit`` / ``meter_and_check`` enforce
    UNCHANGED. Raises ``ValueError`` for a malformed appetite (never a silent
    cap). A size-enum→amount table (read-live) is a deferred enhancement.
    """
    reasons = _appetite_reasons(appetite)
    if reasons:
        raise ValueError(f"appetite is not derivable to a spend_envelope: {'; '.join(reasons)}")
    return {
        "scope": "run",
        "amount": appetite["amount"],
        "unit": appetite["unit"],
        "window": appetite.get("window", "per_run"),
    }


# ---------------------------------------------------------------------------
# State-as-projection over the conserved spec-lifecycle (PURE)
# ---------------------------------------------------------------------------
def project_scope_state(
    scope: Any,
    *,
    dor_ready: bool = False,
    bet_placed: bool = False,
    dispatched: bool = False,
    reviewed: bool = False,
    final_ratified: bool = False,
    merged: bool = False,
) -> dict[str, str]:
    """Project the Scope's state from committed signals (PURE; never an FSM write).

    Computes the highest-reached CONSERVED spec-lifecycle state from the gate
    signals, then exposes the canon cognitive ``phase`` + ``board`` label via the
    dual-mapping. ``ready`` requires BOTH ``dor_ready`` and ``bet_placed`` (the
    front gate). The signals default to a Scope's own ``is_ratified`` +
    ``scope_is_ready`` when not supplied. Returns ``{state, phase, board}``.
    """
    if bet_placed is False and is_ratified(scope):
        bet_placed = True
    if dor_ready is False and scope_is_ready(scope)[0]:
        dor_ready = True
    if merged:
        state = "done"
    elif final_ratified:
        state = "ratified"
    elif reviewed:
        state = "verified"
    elif dispatched:
        state = "in_progress"
    elif dor_ready and bet_placed:
        state = "ready"
    else:
        state = "draft"
    return {"state": state, "phase": cognitive_phase(state), "board": board_label(state)}


# ---------------------------------------------------------------------------
# The dispatch-assembly seam — a ratified Scope → ONE G-4/G-5-governed run (PURE)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DispatchPlan:
    """The inputs for ONE governed run assembled from a ratified, DoR-valid Scope.

    ``runtime_policy`` is the inner-loop policy with the appetite-derived
    ``run``-scope spend envelope merged in (additive — alongside any operator-set
    ``global``/``fleet`` envelopes; most-restrictive-wins still holds). The LIVE
    drive (``make_run_driver``/``run_plan``) is a deferred seam — this is the
    pure assembly that PRODUCES the inputs.
    """

    scope_id: str
    runtime_policy: dict[str, Any]
    mutation_class: str
    scope_ratification: dict[str, Any]  # value-free opaque digests


@dataclass(frozen=True)
class DispatchRefusal:
    """A refusal to dispatch — the front gate was not satisfied (PURE)."""

    reason: str  # "not_ready" | "not_ratified"
    detail: tuple[str, ...] = ()


def assemble_dispatch(scope: Any, runtime_policy: dict[str, Any]) -> DispatchPlan | DispatchRefusal:
    """Assemble the inputs for ONE governed run from a Scope, or REFUSE (PURE).

    The front gate: REFUSES (``not_ready`` / ``not_ratified``) unless the Scope is
    DoR-valid AND a bet is placed. On success, derives the appetite→cap envelope
    and merges it additively into the run's ``runtime_policy.spend_envelopes``,
    returning a :class:`DispatchPlan`. Does NOT spawn the run — the live drive is
    deferred. Pure: never mutates the inputs.
    """
    ready, reasons = scope_is_ready(scope)
    if not ready:
        return DispatchRefusal("not_ready", tuple(reasons))
    if not is_ratified(scope):
        return DispatchRefusal("not_ratified", ("missing or invalid bet ratification binding",))
    envelope = appetite_to_spend_envelope(scope["appetite"])
    policy = dict(runtime_policy or {})
    policy["spend_envelopes"] = list(policy.get("spend_envelopes") or []) + [envelope]
    return DispatchPlan(
        scope_id=str(scope["scope_id"]),
        runtime_policy=policy,
        mutation_class=str(scope["mutation_class"]),
        scope_ratification=dict(scope["ratification"]),
    )
