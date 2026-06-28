---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0013
title: "Authority is substrate-independent; agent-autonomous review and approval gated by role and ratified run-mode"
status: accepted
date: "2026-06-28"
decision_makers: ["ce-gate-architect"]
consulted: ["chmod735"]
informed: []
review_by: "2026-12-28"
mutation_class: governance
evidence_refs:
  - kind: session
    ref: "Operator-ratified principle, 2026-06-28 CEO-Mode governed-autonomy ratification discussion (4 enumerated sub-principles)"
    tag: operator-ratification
  - kind: session
    ref: "Operator direction, 2026-06-28: authority model must be action-centric (autonomous vs reserved verbs), not grant-numbered or substrate-coupled"
    tag: action-taxonomy-direction
  - kind: doc
    ref: "docs/design/ce-orchestrator-agent.md — proposes the controller action-taxonomy this ADR ratifies"
    tag: orchestrator-design-616
  - kind: adr
    ref: "docs/decisions/ADR-0007-egress-gateway-publish-broker.md — egress/credential separation from containment"
    tag: adr-0007
  - kind: doc
    ref: "docs/operations/REVIEWER_VENUE_AUTHORITY.md — G2.007.2/G2.007.3 reviewer-authority-envelope seam"
    tag: g2-007-reviewer-authority
  - kind: issue
    ref: "internal governance: run-mode parameterization of the never-APPROVE guard (AutoReview; CLOSED)"
    tag: run-mode-parameterization
  - kind: issue
    ref: "internal governance: strangeLoop C-cluster coordination and governed autonomy lane"
    tag: strangeloop-lane
  - kind: issue
    ref: "internal governance: CEO-mode policy-tiered auto-merge (Wave 1.1; CLOSED)"
    tag: ceo-mode-automerge
  - kind: issue
    ref: "internal governance: SO_PEERCRED self-push socket attestation for the egress broker (CLOSED)"
    tag: socket-attestation
  - kind: code
    ref: "tools/egress-broker/ce_egress_self_review_broker.py:170-171 — conflated APPROVE refusal"
    tag: conflation-broker
  - kind: code
    ref: "validators/creator_engine_validator/forge/cred_injection_proxy.py:376-378 — conflated APPROVE refusal"
    tag: conflation-proxy
  - kind: adr
    ref: "ce-ops decision-records/ADR-0003-reviewer-independence-isolation-domain.md (ce-ops private repo)"
    tag: adr-0003
  - kind: adr
    ref: "ce-ops decision-records/ADR-0004-agent-containment-eligibility.md (ce-ops private repo)"
    tag: adr-0004
ratification:
  ratified_by: "chmod735"
  ratified_at: "2026-06-28"
  ratification_prompt_sha: "7fec84fca673b03a26307590107bc09326bd4aa0ff34782312ae4255fe723da6"
  quorum: n1_solo
crosswalk:
  informs:
    - ADR-0007
    - "internal: run-mode parameterization of the never-APPROVE guard"
    - "internal: strangeLoop coordination lane"
    - "internal: CEO-mode policy-tiered auto-merge engine"
---

# Authority is substrate-independent; agent-autonomous review and approval gated by role and ratified run-mode

> **Traceability note:** Precise internal governance linkage (issue numbers, sprint references)
> is maintained in the internal decision-record companion, not in this public record.

## Context and Problem Statement

### The operator-ratified principle (2026-06-28)

The following four sub-principles were ratified by the Operator in the CEO-Mode governed-autonomy ratification
discussion on 2026-06-28. They are recorded here as the grounding for this ADR.

1. **Containment is not authority.** Containment is an isolation and runtime substrate
   only. A contained seat — controller, reviewer, or builder — has the full capability
   set of a non-contained one. Containment must never reduce a seat's authority.

2. **Agent-autonomous review and approval is the direction.** Frontier labs already have
   approximately 100% of code agent-authored; agents operating orders of magnitude faster
   means approximately 100% of PR and security reviews will also be agent-performed and
   approved autonomously. CE is going there.

3. **Human-rooted ratification moves up to the policy level.** The human ratification
   gesture belongs at the ratified run-mode, reviewer-authority-envelope, or CEO-mode /
   strangeLoop level — not at each individual PR click.

4. **The only legitimate review wall is author-not-equal-approver.** APPROVE must be
   gated by role (author vs independent reviewer) and ratified run-mode policy, not by
   substrate (containment).

### The existing conflation

The current code conflates two orthogonal concerns: containment (substrate) and approval
authority (role-and-run-mode). Specifically:

- `tools/egress-broker/ce_egress_self_review_broker.py` at lines 170-171 hard-refuses
  APPROVE with the reason "APPROVE is controller approval-wall only; host broker refuses it."
  The broker enforces this as an unconditional constant, regardless of whether the requesting
  seat is the PR's author or an independent reviewer under a ratified run-mode.

- `validators/creator_engine_validator/forge/cred_injection_proxy.py` at lines 376-378
  repeats the refusal in `_validate_contained_review`: "APPROVE is controller approval-wall
  only," and the `_CONTAINED_REVIEW_EVENTS` frozenset at line 44 excludes APPROVE entirely.
  `ContainedSeatReview`'s docstring (lines 124-128) encodes the same restriction as a class
  invariant: "Contained seats may submit only opinionated non-approval reviews through this
  seam; gate-valid approvals remain controller-only approval-wall work."

The framing "contained seats may not APPROVE" and "controller-only approval-wall" couples
the APPROVE decision to the containment substrate rather than to the role identity and
run-mode. This violates Principle 1 and Principle 4 above.

The correct model: APPROVE must be refused when the requesting seat is the PR author
(the author-not-equal-approver invariant, which is correctly checked at lines 237-244 of
the broker and is a legitimate and load-bearing guard). APPROVE must be allowed for an
independent (non-author) reviewer seat under the active ratified run-mode plus a valid
reviewer-authority-envelope. Whether that seat is contained is irrelevant.

### Related prior work

- **ADR-0007** (egress gateway/publish broker) establishes that containment governs
  egress-path privilege — which agent may hold forge push credentials — not review
  authority. An agent that cannot push may still hold review authority.
- **G2.007.2 / G2.007.3** (`docs/operations/REVIEWER_VENUE_AUTHORITY.md`) built the
  reviewer-authority-envelope seam: a bounded, auditable envelope authorizes exactly one
  `pr_review` mechanic on exactly one PR, keyed to role (`reviewer`) and lane kind (`review`).
  This seam is exactly the right primitive for authority-by-role; it is not yet wired to
  the broker/herdr path.
- The run-mode parameterization of the never-APPROVE guard (closed) identified the
  never-APPROVE guard as a hardcoded constant that should instead flow from the run-mode,
  and noted that strangeLoop may need APPROVE under a deliberate governance decision.
- The CEO-mode policy-tiered auto-merge engine (closed) built the policy-tiered
  auto-merge run-mode engine (dry-run mode), which parameterizes what is allowed without
  a per-PR human gesture.
- The strangeLoop coordination lane is the long-pole autonomous-review endpoint: a governed
  coordination loop where the loop itself constitutes the governance path.
- **ce-ops ADR-0003** (reviewer-independence-isolation-domain, private ce-ops repo) and
  **ce-ops ADR-0004** (agent-containment-eligibility, private ce-ops repo) are the
  upstream decision records this ADR composes with; ADR-0003 defines the
  author-not-equal-approver boundary and ADR-0004 maps containment to eligibility for
  certain reviewer-dispatch paths. Neither ADR couples APPROVE authority to containment.

## Decision Drivers

- The Operator-ratified principle (four sub-principles above) is the governing authority.
- The author-not-equal-approver guard is load-bearing and must be preserved.
- The run-mode parameterization of the never-APPROVE guard and the reviewer-authority-envelope
  from G2.007.2/G2.007.3 are already the right primitives; they need wiring, not redesign.
- Fail-closed posture must be preserved: no weakening of default deny; APPROVE under a
  ratified run-mode is an explicit grant, not a default.
- ADR-0007's TCB-minimization discipline still applies to egress; this ADR is about
  review authority, not forge push authority.

## Decision

### D1 — Authority is defined by an action-taxonomy, not by grant-numbers or by substrate

Controller authority is defined by **classifying every action a controller performs on a
routine basis as either _autonomous_ or _reserved_**, with the predicates that gate the
autonomous ones. This supersedes the prior ad-hoc "G1–G5" banded-grant framing, whose
lineage was terse pointer shorthand (`#249` / wall / autonomy-canary) recorded only in
resume-state checkpoints and never authoritative. An ADR band must carry a *semantic
description of the action it authorizes*, not a ticket pointer.

**Autonomous — routine delivery actions, permitted when their predicates hold:**

| Action (verb) | Gated by |
|---|---|
| intake · territory-map · claim-or-skip | record skip reason; collision-check before claim |
| dispatch (role-shaped, self-contained brief) | file-disjoint vs other seats/PRs; least-authority role; pointer+hash |
| watch · validate/preflight · rerun-transient-check · return-to-author | no scope or credential broadening |
| harvest worker output | output matches brief + stop-line; changed paths in scope |
| route independent review · submit reviewer verdict | author ≠ reviewer |
| merge / gate | independent review + green CI + declared work-class + ratification + never-red-under-grant + in-arc |
| open / update ordinary delivery PR | within the active run-mode |
| conveyor next-lane · batch dispatch | dependency order + author/reviewer separation + file-disjointness |
| checkpoint / emit resume-state | — |
| model / effort routing | execution detail only — MUST NOT broaden mounts, credentials, egress, or action authority |

**Reserved — HALT until the Operator supplies authority:** release · sign · publish ·
deploy · fleet rollout/arming (including the first live auto-merge flip and strangeLoop
arming) · history scrub · weakening a guard or a new policy exception · broadening a
worker's mount/egress/credentials/path authority beyond its dispatched envelope ·
irreversible destructive work · new / ambiguous / high-consequence scope · merging with
any missing predicate · acting when direct evidence contradicts remembered or recalled state.

**Governing principle:** *Autonomous = reversible, in-policy, predicate-satisfied delivery
actions. Reserved = anything irreversible, governance-altering, scope-expanding, or
authority-minting.* The human ratification gesture attaches to the run-mode and to the
reserved set — not to each individual autonomous action.

This taxonomy is the authority model proposed in the CE Orchestrator Agent design
(`docs/design/ce-orchestrator-agent.md`); this ADR is the decision record that ratifies it.

### D2 — Authority is substrate-independent

**Containment is a runtime substrate concern and carries no authority implication.** The
taxonomy in D1 holds identically whether the acting surface is a Codex seat, a Claude-Code
pane, a server-side agent runtime, a GitHub App, a local CLI, or a future CEO-mode cockpit.
The substrate may change *how* an action executes; it never changes *who may decide it*,
*which predicates must hold*, or *which actions are reserved*. A contained seat —
controller, reviewer, or builder — has the full capability set of a non-contained one.

### D3 — Worked application: review and APPROVE

The clearest live instance of the D2 principle is the review wall. A contained seat that is
an independent reviewer under a ratified run-mode and a valid reviewer-authority-envelope
MUST be permitted to submit APPROVE.

**The only legitimate review wall is:** the requesting seat must not be the PR author (the
author-not-equal-approver invariant). This check must remain and must be enforced before any
credential is minted.

**APPROVE is gated by role and run-mode, not by containment.**

The gating logic is:

1. **Author-not-equal-approver check (always enforced, fail-closed).** The requesting
   seat's review identity must differ from the PR's resolved author. This check runs before
   any credential is minted and before any event type is evaluated. It is not a fallback; it
   is the primary review wall.

2. **Reviewer-authority-envelope validation (required for APPROVE).** An APPROVE submission
   requires a valid, schema-conformant reviewer-authority-envelope (as defined by G2.007.2):
   mechanic=`pr_review`, pr_number matching the request, emitting_role=`reviewer`,
   operating_mode compatible with the active run-mode. The envelope must be minted out-of-band
   under the ratified reviewer-launch procedure (tied to the ratified reviewer prompt).

3. **Run-mode policy check (required for APPROVE).** The active run-mode must permit
   autonomous APPROVE. For the current run-modes (`solo`, `team`), autonomous APPROVE
   remains gated on the Operator ratification gesture at the run-mode level (not per-PR).
   For a future explicitly-ratified `strangeLoop` run-mode (the strangeLoop coordination
   lane), the loop itself constitutes the governance path, and APPROVE may be permitted
   under the envelope. The run-mode is a configuration of the system, not a per-request flag.

4. **Substrate is not checked.** Whether the reviewer seat is contained or uncontained
   is not a factor in whether APPROVE is permitted or denied.

## Consequences of adopting this decision

**Good:**

- Aligns the code with the ratified Operator principle. Containment and review authority
  are orthogonal; coupling them was an implementation shortcut, not a governance requirement.
- Unblocks agent-autonomous review under ratified run-modes (the strangeLoop endgame and
  the near-term CEO-mode auto-review-and-approve path).
- The author-not-equal-approver wall is preserved and strengthened: it is now clearly the
  primary invariant, not a footnote next to a containment check.
- The reviewer-authority-envelope seam (G2.007.2/G2.007.3) provides exactly the right
  primitive: a bounded, auditable, per-PR grant that carries role and run-mode bindings.

**Trade-offs:**

- The broker and proxy must be modified: `_CONTAINED_REVIEW_EVENTS` must expand to include
  APPROVE under the conditions above; `_validate_contained_review` must be refactored to
  accept APPROVE when the envelope and run-mode checks pass; the broker `parse_request`
  and `ALLOWED_EVENTS` constant must be parameterized by run-mode.
- The reviewer-authority-envelope must be wired to the broker/herdr path (G2.007.3 wiring
  deferred to the follow-on ticket). Until wired, the default-deny posture is preserved by
  failing closed on a missing or invalid envelope.
- The run-mode integration must be tested before any live APPROVE is permitted: dry-run
  classify-only mode must gate the first live flip (same discipline as the CEO-mode
  policy-tiered auto-merge engine).
- The `ContainedSeatReview` docstring and the broker module-level docstring must be
  rewritten to reflect the correct model (role+run-mode wall, not containment wall).

## Relationship to existing ADRs and prior work

| Prior artifact | Relationship |
|---|---|
| ADR-0007 (egress broker) | Orthogonal: ADR-0007 governs forge push egress; this ADR governs review authority. An agent that cannot push may still APPROVE a PR as an independent reviewer. |
| ce-ops ADR-0003 (reviewer independence) | This ADR composes with ADR-0003: the author-not-equal-approver rule from ADR-0003 is preserved and is the primary wall here. |
| ce-ops ADR-0004 (containment eligibility) | ADR-0004 maps containment to reviewer-dispatch eligibility (e.g. an uncontained/advisory seat is ineligible). This ADR does not contradict that: a contained seat satisfying ADR-0004 is eligible. This ADR adds that being contained does not cap the reviewer's authority once eligible. |
| G2.007.2 / G2.007.3 (reviewer-authority-envelope) | The reviewer-authority-envelope is the implementation primitive for role+run-mode-gated APPROVE. This ADR requires its use. G2.007.3 wiring to the broker/herdr path is the implementation dependency. |
| run-mode parameterization of the never-APPROVE guard | This ADR ratifies the principle that the referenced internal governance work identified: the never-APPROVE guard must be a run-mode-keyed policy, not a constant. This ADR is the written decision; that work surfaced the gap. |
| CEO-mode policy-tiered auto-merge engine | The CEO-mode policy engine provides the run-mode infrastructure. APPROVE permission in a given run-mode is a policy decision encoded in that engine. |
| strangeLoop coordination lane | strangeLoop is the autonomous-review endpoint. The APPROVE permission under strangeLoop is an explicit governance decision to be made when strangeLoop is scoped; this ADR clears the way for it. |

## What this ADR does NOT decide

- The definition of the strangeLoop run-mode or the specific conditions under which APPROVE
  is permitted within it. That is tracked in the strangeLoop coordination lane governance item.
- The exact implementation shape of the broker/proxy modification. That is the engineering
  ticket to be filed.
- The wiring of the reviewer-authority-envelope to the herdr path. That is G2.007.3
  completion (deferred, not in this ADR).
- Any relaxation of the fail-closed posture for cases without a valid envelope.

## Ratification

Ratified by Operator **chmod735** on **2026-06-28** via this ADR's ratification record.
Promoted from the governance research draft (sha256 prefix `7fec84fc`, 294 lines)
to `docs/decisions/ADR-0013-substrate-independent-authority.md` via a governance PR.

The substrate-independence body (D2/D3) was drafted by a governed worker under the
Operator-ratified principle; the action-taxonomy (D1) was authored by the Orchestrator
under direct Operator direction on 2026-06-28 (the decision to make authority
action-centric rather than grant-numbered).

The broker/proxy modification this ADR motivates is the separate ratified implementation
ticket (tracked separately), which requires its own full preflight pass before merging.
