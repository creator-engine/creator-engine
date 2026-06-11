"""CE v3.5-B.1 — the ``CE_DEMO=1`` seed (Fork F-b: its OWN module). PURE constructor.

The seeded fleet that tells the grader-outside story on camera (design §3.3):
~8 seats across all five canon columns, with ONE blocked seat that attempted
``git push`` and was DENIED by the deploy boundary — the visible form of "the
grader lives outside the agent". The seed is the pitch artifact, so it is its
own independently-reviewable module (Fork F-b, ratified) and every record is
**L1-shaped and schema-true**:

* pane records validate against ``schemas/pane-registry.schema.yaml``;
* Scope records validate against ``schemas/scope.schema.yaml``;
* evidence records are hash-chained via the shared
  ``runtime_evidence_spine.append`` so ``verify_chain() == []`` on every seed
  chain — the demo's tamper-evidence is REAL, only its data is seeded (and the
  persistent "DEMO — seeded data, not a live fleet" watermark says so).

PURE: a deterministic constructor — no disk, subprocess, socket, clock, or rng
(timestamps are fixed constants; the story is set on the morning of
2026-07-01). The fold lives in ``runner.cockpit_readmodel``; ``seed()`` returns
exactly its ``fold_snapshot`` keyword inputs.

Join rule (documented in the read-model): a seed chain's ``run_id`` equals the
seat's ``lane_id``, which is how the board attributes evidence to seats.

Defensive only — seeded demo data for a read-only governance view.
"""

from __future__ import annotations

import hashlib
from typing import Any

from ..runtime_evidence_spine import (
    RUNTIME_AGENT_ACTION_RECORD_KIND,
    RUNTIME_AGENT_ACTION_RECORD_TYPE,
    RUNTIME_SPEND_BREACH_RECORD_KIND,
    RUNTIME_SPEND_BREACH_RECORD_TYPE,
    RUN_OUTCOME_RECORD_KIND,
    RUN_OUTCOME_RECORD_TYPE,
    append,
)
from .spend_gate import meter_record_body

#: The seed's value-free policy binding — a deterministic digest, never a real
#: runtime-policy (the watermark declares the data seeded).
DEMO_POLICY_SHA = hashlib.sha256(b"ce-cockpit-demo-policy").hexdigest()

#: A value-free 64-hex ratifier digest for the seeded bets.
_DEMO_APPROVER = hashlib.sha256(b"ce-cockpit-demo-operator").hexdigest()
_DEMO_SCOPE_SHA = hashlib.sha256(b"ce-cockpit-demo-scope-body").hexdigest()

#: The deploy-boundary refusal reason, mirroring the Ring-1 hook's exact clause
#: (``hook_check._mechanics_would_deny``) — the demo shows the REAL boundary.
PUSH_DENY_REASON = (
    "restricted mechanic (deploy) is denied without a matching ratified "
    "reviewer-venue side-effect-authority envelope (G2.007.2)"
)

#: The envelope-scope denial (v3.5-B.3): a pr_review attempted OUTSIDE the
#: envelope's pr_number — textbook IMPLICIT deny (not covered by any grant; no
#: deciding clause cited).
ENVELOPE_SCOPE_DENY_REASON = (
    "pr_review on PR 311 is not covered by envelope rva-demo-pr300 "
    "(its grant is pr_number: 300) — implicit deny"
)

HARD_BREACH_ESCALATION_ID = hashlib.sha256(b"ce-cockpit-demo-hard-breach").hexdigest()

#: The seeded reviewer-authority envelope (schema-true per
#: ``schemas/reviewer-authority-envelope.schema.yaml``): exactly ONE mechanic
#: on exactly ONE PR, with the ratifier attribution the panel renders.
DEMO_ENVELOPE = {
    "envelope_id": "rva-demo-pr300",
    "mechanic": "pr_review",
    "pr_number": 300,
    "head_sha": "f00dfeed1234",
    "actor": "demo-reviewer-account",
    "ratified_prompt_sha": hashlib.sha256(b"ce-cockpit-demo-ratified-prompt").hexdigest(),
    "emitting_role": "operator",
    "operating_mode": "strict",
    "recorded_at": "2026-07-01T09:09:00Z",
}

_HOST = "demo-host"


def _ts(minute: int) -> str:
    """A fixed demo timestamp on the 01-Jul-2026 demo morning (PURE constant)."""
    return f"2026-07-01T09:{minute:02d}:00Z"


def _chain(bodies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hash-chain record bodies via the shared spine (PURE)."""
    chain: list[dict[str, Any]] = []
    for body in bodies:
        chain.append(append(chain, body))
    return chain


def _action(
    run_id: str,
    minute: int,
    *,
    op: str,
    mutation_class: str,
    target: str,
    tool: str,
    classification: str,
    decision_mode: str,
    decision_reason: str,
) -> dict[str, Any]:
    """One ``runtime_agent_action`` record body (Tier-B fidelity, pre timing)."""
    return {
        "kind": RUNTIME_AGENT_ACTION_RECORD_KIND,
        "record_type": RUNTIME_AGENT_ACTION_RECORD_TYPE,
        "schema_version": "1",
        "policy_sha": DEMO_POLICY_SHA,
        "run_id": run_id,
        "recorded_at": _ts(minute),
        "op": op,
        "mutation_class": mutation_class,
        "target": target,
        "tool": tool,
        "fidelity": "best_effort",
        "timing": "pre",
        "classification": classification,
        "decision_mode": decision_mode,
        "decision_reason": decision_reason,
    }


def _outcome(run_id: str, minute: int, *, outcome: str, branch: str, pr_number: int) -> dict[str, Any]:
    """One terminal ``runtime_run_outcome`` record body (value-free change_set)."""
    return {
        "kind": RUN_OUTCOME_RECORD_KIND,
        "record_type": RUN_OUTCOME_RECORD_TYPE,
        "schema_version": "1",
        "policy_sha": DEMO_POLICY_SHA,
        "run_id": run_id,
        "recorded_at": _ts(minute),
        "outcome": outcome,
        "change_set": {
            "branch": branch,
            "base": "main",
            "manifest_paths": ["docs/demo-change.md"],
            "head_sha": hashlib.sha256(f"demo-head-{run_id}".encode()).hexdigest()[:12],
            "pr_number": pr_number,
        },
    }


def _lifecycle(run_id: str, minute: int, phase: str) -> dict[str, Any]:
    """One ``runtime_evidence`` lifecycle attestation (the waterfall's input)."""
    return {
        "kind": "runtime-evidence-record",
        "record_type": "runtime_evidence",
        "schema_version": "1",
        "policy_sha": DEMO_POLICY_SHA,
        "run_id": run_id,
        "recorded_at": _ts(minute),
        "lifecycle_phase": phase,
        "classification": "allowed",
    }


def _ratification(run_id: str, minute: int) -> dict[str, Any]:
    """One value-free ``runtime_ratification`` record (the Outcome tab's input)."""
    return {
        "kind": "runtime-ratification",
        "record_type": "runtime_ratification",
        "schema_version": "1",
        "policy_sha": DEMO_POLICY_SHA,
        "run_id": run_id,
        "recorded_at": _ts(minute),
        "ratified_prompt_sha": hashlib.sha256(f"demo-ratified-{run_id}".encode()).hexdigest(),
        "approver_ref": _DEMO_APPROVER,
        "ratified_head_sha": hashlib.sha256(f"demo-head-{run_id}".encode()).hexdigest()[:12],
        "binding_ref": hashlib.sha256(f"demo-binding-{run_id}".encode()).hexdigest(),
    }


def _ledger_leaf(run_id: str, minute: int, amount: float, model: str) -> dict[str, Any]:
    """One metered ``runtime_spend_ledger`` leaf via the REAL G-5 builder (PURE)."""
    return meter_record_body(
        policy_sha=DEMO_POLICY_SHA,
        run_id=run_id,
        recorded_at=_ts(minute),
        amount=amount,
        unit="$",
        fleet_id="demo-fleet",
        model=model,
        window="per_run",
    )


def _pane(
    controller_id: str,
    lane_id: str,
    *,
    role: str,
    status: str,
    minute: int,
    pane_n: int,
    closed: bool = False,
    envelope_ref: str | None = None,
) -> dict[str, Any]:
    """One schema-true pane-registry record (PURE)."""
    record: dict[str, Any] = {
        "kind": "pane-registry-record",
        "record_type": "pane_identity",
        "schema_version": "1",
        "controller_id": controller_id,
        "lane_id": lane_id,
        "claim_ref": f"claims/{controller_id}/{lane_id}.yaml",
        "host_id": _HOST,
        "pane_id": f"pane-demo{pane_n:02d}",
        "role": role,
        "status": status,
        "record_timestamp": _ts(minute),
        "registered_at": _ts(max(minute - 10, 0)),
        "last_seen_at": _ts(minute),
        "visibility": "operator_visible",
        "terminal": {
            "kind": "tmux",
            "session_id": "$demo",
            "window_id": "@1",
            "pane_id": f"%{pane_n}",
        },
        "branch": f"ce/demo/{lane_id}",
    }
    if closed:
        record["closed_at"] = _ts(minute)
        record["close_reason"] = "completed"
    if envelope_ref is not None:
        record["envelope_ref"] = envelope_ref
    return record


def _scope(
    scope_id: str,
    intent: str,
    *,
    mutation_class: str,
    done_when: list[str] | None = None,
    budget: float | None = None,
    ratified: bool = False,
) -> dict[str, Any]:
    """One schema-true Scope record (PURE)."""
    scope: dict[str, Any] = {
        "kind": "scope-record",
        "record_type": "scope",
        "schema_version": "1",
        "scope_id": scope_id,
        "intent": intent,
        "mutation_class": mutation_class,
    }
    if done_when:
        scope["acceptance_criteria"] = list(done_when)
    if budget is not None:
        scope["appetite"] = {"amount": budget, "unit": "$", "window": "per_run"}
    if ratified:
        scope["ratification"] = {
            "approver_ref": _DEMO_APPROVER,
            "ratified_scope_sha": _DEMO_SCOPE_SHA,
        }
    return scope


def _dispatch(
    scope_id: str,
    *,
    mutation_class: str,
    spawned_minute: int,
    spend_envelope: dict[str, Any],
    collected_minute: int | None = None,
    resource_bound: Any = None,
) -> dict[str, Any]:
    """One demo dispatch wrapper: schema-true record + sibling policy projection."""
    record: dict[str, Any] = {
        "kind": "dispatch-record",
        "record_type": "dispatch",
        "schema_version": "1",
        "scope_id": scope_id,
        # Demo join rule: run_id equals the seat lane_id, like the evidence chains.
        "run_id": scope_id,
        "mutation_class": mutation_class,
        "scope_ratification": {
            "approver_ref": _DEMO_APPROVER,
            "ratified_scope_sha": _DEMO_SCOPE_SHA,
        },
        "harness": "claude",
        "unattended": True,
        "session": "ce-demo",
        "window": "drive",
        "runtime_policy_ref": f"demo/dispatches/{scope_id}/runtime-policy.yaml",
        "brief_ref": f"demo/dispatches/{scope_id}/brief.md",
        "terminal": {
            "kind": "tmux",
            "session_id": "$demo",
            "window_id": "@1",
            "pane_id": f"%demo-{scope_id}",
        },
        "resource_bound": resource_bound,
        "spawned_at": _ts(spawned_minute),
        "collected_at": _ts(collected_minute) if collected_minute is not None else None,
    }
    return {"dispatch": record, "spend_envelope": dict(spend_envelope)}


def seed() -> dict[str, Any]:
    """Return the L1-shaped demo fleet — exactly ``fold_snapshot``'s keyword inputs (PURE)."""
    panes = [
        _pane("ce-demo-framer", "scope-billing-frame", role="architect", status="active", minute=2, pane_n=1),
        _pane("ce-demo-shaper", "scope-meter-shape", role="architect", status="active", minute=5, pane_n=2),
        _pane("ce-demo-builder-a", "gate-uploads", role="implementer", status="active", minute=8, pane_n=3),
        # THE demo seat: refused `git push` by the deploy boundary -> blocked.
        # envelope_ref=none = the registry's no-write-authority marker.
        _pane("ce-demo-builder-b", "gate-push-refusal", role="implementer", status="blocked", minute=14, pane_n=4,
              envelope_ref="none"),
        _pane("ce-demo-reviewer", "pr-300-review", role="reviewer", status="active", minute=11, pane_n=5,
              envelope_ref="envelopes/rva-demo-pr300.yaml"),
        # Envelope-scope denial seat (tried a PR outside its envelope's pr_number).
        _pane("ce-demo-scout", "envelope-scope-denial", role="reviewer", status="active", minute=12, pane_n=6),
        # Spend hard-breach seat (paused at 100% of its run envelope).
        _pane("ce-demo-spender", "spend-hard-breach", role="implementer", status="blocked", minute=13, pane_n=7),
        _pane("ce-demo-shipper", "ship-pr-294", role="implementer", status="closed", minute=15, pane_n=8, closed=True),
    ]

    # Scope ids equal their seats' lane_ids (the documented board join rule —
    # a lane allocated FOR a Scope is named after it).
    scopes = [
        _scope("scope-billing-frame", "frame the metered-billing probe", mutation_class="docs"),
        _scope(
            "scope-meter-shape", "shape the meter-tile slice",
            mutation_class="code", done_when=["tiles render with badges"], budget=8.0, ratified=True,
        ),
        _scope(
            "gate-uploads", "gate the upload pipeline",
            mutation_class="code", done_when=["gate denies oversize uploads"], budget=12.0, ratified=True,
        ),
        _scope(
            "gate-push-refusal", "land the release branch",
            mutation_class="deploy", done_when=["release branch green"], budget=15.0, ratified=True,
        ),
        _scope(
            "pr-300-review", "independently review PR 300",
            mutation_class="governance", done_when=["review submitted through the hook"], budget=5.0, ratified=True,
        ),
        _scope(
            "envelope-scope-denial", "probe a review outside the envelope",
            mutation_class="governance", done_when=["denial recorded on the spine"], budget=3.0, ratified=True,
        ),
        _scope(
            "spend-hard-breach", "migrate the demo dataset",
            mutation_class="schema", done_when=["migration replayed clean"], budget=10.0, ratified=True,
        ),
        _scope(
            "ship-pr-294", "ship the docs refresh (PR 294)",
            mutation_class="docs", done_when=["PR 294 merged head-pinned"], budget=4.0, ratified=True,
        ),
    ]

    # Committed-signal projections (state-as-projection; the seed states the
    # signals, project_scope_state derives the conserved state).
    scope_signals = {
        "gate-uploads": {"dispatched": True},
        "gate-push-refusal": {"dispatched": True},
        "envelope-scope-denial": {"dispatched": True},
        "spend-hard-breach": {"dispatched": True},
        "pr-300-review": {"reviewed": True},
        "ship-pr-294": {"merged": True},
    }

    chains = {
        # The 01-Jul moment: an allowed in-manifest write, then `git push`
        # DENIED by the deploy boundary — TWICE (a Temporal-style retry span
        # on the Stream tab) — on a verifying hash chain.
        "gate-push-refusal": _chain([
            _action(
                "gate-push-refusal", 13,
                op="write", mutation_class="code",
                target="src/release/notes.md", tool="Edit",
                classification="allowed", decision_mode="allowlist",
                decision_reason="permitted under active manifest / mechanics / secret policy",
            ),
            _action(
                "gate-push-refusal", 14,
                op="vcs", mutation_class="deploy",
                target="git push origin ce/demo/gate-push-refusal", tool="Bash:git push",
                classification="denied", decision_mode="deny",
                decision_reason=PUSH_DENY_REASON,
            ),
            _action(
                "gate-push-refusal", 15,
                op="vcs", mutation_class="deploy",
                target="git push origin ce/demo/gate-push-refusal", tool="Bash:git push",
                classification="denied", decision_mode="deny",
                decision_reason=PUSH_DENY_REASON,
            ),
        ]),
        # The reviewer seat: a clean chain ending in review_submitted.
        "pr-300-review": _chain([
            _action(
                "pr-300-review", 10,
                op="egress", mutation_class="governance",
                target="pr#300", tool="Bash:gh pr review",
                classification="allowed", decision_mode="allowlist",
                decision_reason="pr_review authorized by envelope rva-demo-pr300 (pr_number 300)",
            ),
            _outcome("pr-300-review", 11, outcome="review_submitted",
                     branch="ce/demo/pr-300-review", pr_number=300),
        ]),
        # The shipped seat: full lifecycle (the Waterfall tab), the terminal
        # pr_merged disposition, and the value-free ratification record.
        "ship-pr-294": _chain([
            _lifecycle("ship-pr-294", 2, "provision"),
            _lifecycle("ship-pr-294", 5, "run"),
            _lifecycle("ship-pr-294", 14, "collect"),
            _outcome("ship-pr-294", 15, outcome="pr_merged",
                     branch="ce/demo/ship-pr-294", pr_number=294),
            _ratification("ship-pr-294", 15),
            _lifecycle("ship-pr-294", 16, "teardown"),
        ]),
        # The fleet's other metered run (v3.5-B.4): two ledger leaves on the
        # active builder, so the MEASURED fleet spend exceeds the breached run
        # — plus two in-manifest writes (the Diffs tab's input).
        "gate-uploads": _chain([
            _ledger_leaf("gate-uploads", 3, 1.80, "claude-fable-5"),
            _action(
                "gate-uploads", 4,
                op="write", mutation_class="code",
                target="src/uploads/gate.py", tool="Edit",
                classification="allowed", decision_mode="allowlist",
                decision_reason="permitted under active manifest / mechanics / secret policy",
            ),
            _action(
                "gate-uploads", 7,
                op="write", mutation_class="code",
                target="src/uploads/gate.py", tool="Edit",
                classification="allowed", decision_mode="allowlist",
                decision_reason="permitted under active manifest / mechanics / secret policy",
            ),
            _ledger_leaf("gate-uploads", 8, 1.50, "claude-fable-5"),
        ]),
        # The spend hard-breach pause: the run's metered leaves ($10.00 of a
        # $10.00 cap) then the chain-true circuit-breaker trip (v3.5-B.3/B.4).
        "spend-hard-breach": _chain([
            _ledger_leaf("spend-hard-breach", 1, 4.00, "claude-opus-4-8"),
            _ledger_leaf("spend-hard-breach", 6, 3.50, "claude-opus-4-8"),
            _ledger_leaf("spend-hard-breach", 12, 2.50, "claude-opus-4-8"),
            {
                "kind": RUNTIME_SPEND_BREACH_RECORD_KIND,
                "record_type": RUNTIME_SPEND_BREACH_RECORD_TYPE,
                "schema_version": "1",
                "policy_sha": DEMO_POLICY_SHA,
                "run_id": "spend-hard-breach",
                "recorded_at": _ts(13),
                "breach_scope": "run",
                "breach_unit": "$",
                "tier": "hard",
                "signal": "budget_exhausted",
                "limit": 10.0,
                "observed": 10.0,
                "decision_reason": (
                    "run spend envelope exhausted (observed $10.00 of $10.00 cap) — "
                    "hard breach: pause + escalate; do NOT retry (budget_exhausted)"
                ),
                "escalation_id": HARD_BREACH_ESCALATION_ID,
            },
        ]),
    }

    # v3.5-B.3 — the hook-side refusal chain the ★ REFUSED feed projects:
    # the refused git push (EXPLICIT deny, deciding clause G2.007.2) and the
    # envelope-scope denial (IMPLICIT deny — not covered by any grant), hash-
    # chained exactly like the live Ring-1 hook writes them.
    refusal_chain = _chain([
        _action(
            "gate-push-refusal", 14,
            op="vcs", mutation_class="deploy",
            target="git push origin ce/demo/gate-push-refusal", tool="Bash:git",
            classification="denied", decision_mode="deny",
            decision_reason=PUSH_DENY_REASON,
        ),
        _action(
            "envelope-scope-denial", 16,
            op="egress", mutation_class="governance",
            target="gh pr review 311 --approve", tool="Bash:gh",
            classification="denied", decision_mode="deny",
            decision_reason=ENVELOPE_SCOPE_DENY_REASON,
        ),
    ])

    observations = [
        {"hookEventName": "PreToolUse", "observedAt": _ts(14), "advisory": True, "blocking": False},
        {"hookEventName": "Stop", "observedAt": _ts(15), "advisory": True, "blocking": False},
    ]

    # v3.5-B.4 — the meter-strip inputs whose LIVE taps are deferred seams:
    # UsageTurn-shaped dicts (the token-rate fold) and the harness's
    # authoritative context-% (CONSUMED, never recomputed; 52% -> a visible
    # 'warn' nudge state, reusing the v3_session thresholds).
    usage_turns = [
        {
            "session_id": "spend-hard-breach", "model": "claude-opus-4-8",
            "recorded_at": _ts(1),
            "usage": {"input_tokens": 52_000, "output_tokens": 9_000,
                      "cache_read_input_tokens": 180_000, "cache_creation_input_tokens": 12_000},
        },
        {
            "session_id": "spend-hard-breach", "model": "claude-opus-4-8",
            "recorded_at": _ts(6),
            "usage": {"input_tokens": 48_000, "output_tokens": 11_000,
                      "cache_read_input_tokens": 210_000, "cache_creation_input_tokens": 8_000},
        },
        {
            "session_id": "gate-uploads", "model": "claude-fable-5",
            "recorded_at": _ts(8),
            "usage": {"input_tokens": 30_000, "output_tokens": 7_500,
                      "cache_read_input_tokens": 120_000, "cache_creation_input_tokens": 6_000},
        },
        {
            "session_id": "spend-hard-breach", "model": "claude-opus-4-8",
            "recorded_at": _ts(12),
            "usage": {"input_tokens": 41_000, "output_tokens": 8_200,
                      "cache_read_input_tokens": 160_000, "cache_creation_input_tokens": 5_000},
        },
    ]

    escalations = [
        {
            "kind": "escalation-record",
            "record_type": "escalation",
            "schema_version": "1",
            "escalation_id": HARD_BREACH_ESCALATION_ID,
            "title": "Spend hard-breach needs Operator decision",
            "decision_needed": "Raise the run cap for spend-hard-breach, or halt the migration?",
            "recommendation": "Halt and re-scope before raising the cap.",
            "created_at": _ts(13),
            "source_ref": "https://github.com/creator-engine/demo/issues/10",
        },
        {
            "kind": "escalation-record",
            "record_type": "escalation",
            "schema_version": "1",
            "escalation_id": "resolved-demo-escalation",
            "title": "Reviewer venue confirmed",
            "decision_needed": "Confirm whether PR 300 review may proceed through the envelope.",
            "recommendation": "Proceed through the ratified PR-300 envelope only.",
            "created_at": _ts(4),
            "source_ref": "https://github.com/creator-engine/demo/issues/8",
            "resolved_at": _ts(9),
            "resolution": "Operator confirmed the PR-300 envelope.",
        },
    ]

    dispatches = [
        _dispatch(
            "gate-uploads",
            mutation_class="code",
            spawned_minute=12,
            spend_envelope={"scope": "run", "amount": 12.0, "unit": "$", "window": "per_run"},
            resource_bound={"unit": "ce-seat-demo-gate-uploads"},
        ),
        _dispatch(
            "ship-pr-294",
            mutation_class="docs",
            spawned_minute=10,
            collected_minute=15,
            spend_envelope={"scope": "run", "amount": 4.0, "unit": "$", "window": "per_run"},
            resource_bound={"unit": "ce-seat-demo-ship-pr-294"},
        ),
    ]

    return {
        "panes": panes,
        "scopes": scopes,
        "scope_signals": scope_signals,
        "chains": chains,
        "observations": observations,
        "refusal_chain": refusal_chain,
        "escalations": escalations,
        "dispatches": dispatches,
        "envelopes": {"pr-300-review": dict(DEMO_ENVELOPE)},
        "usage_turns": usage_turns,
        "context_pct": 52.0,
        # Harness provenance (live: the governance sidecar beside each pane
        # record); the demo fleet is deliberately mixed-harness.
        "harnesses": {
            "scope-billing-frame": "claude",
            "scope-meter-shape": "codex",
            "gate-uploads": "claude",
            "gate-push-refusal": "claude",
            "pr-300-review": "claude",
            "envelope-scope-denial": "codex",
            "spend-hard-breach": "claude",
            "ship-pr-294": "claude",
        },
    }
