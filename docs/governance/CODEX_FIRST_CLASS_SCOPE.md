# CFC-1: Codex First-Class Actor Envelope — Governance Scope

**Backlog id**: `post-sprint-0/cfc-1-codex-first-class`
**Batch**: 1 (governance/docs scope and protocol authoring)
**Mutation class**: `governance` / `docs`
**Ratifier**: `source` only
**Status**: Landed — merged on canonical origin/main via PR #25 / merge commit `30a3e8c`

## 1. Purpose

This document defines the bounded governance scope for CFC-1 Batch 1.
CFC-1 creates the substrate that will later allow Codex to operate as a
first-class governed actor in Creator Engine workflows. Batch 1 does not
instantiate that actor; it establishes the scope boundaries and
operational protocol that any future Codex-as-actor work must respect.

**Core policy (settled by the reconciled Sonnet/Opus architecture decision)**:

> Opus shapes the envelope when the envelope itself matters. Sonnet
> executes the envelope when the envelope is already settled.

For this gate, the envelope is settled. Batch 1 executes the bounded
docs implementation; it does not reshape or broaden the envelope.

## 2. What Batch 1 is

Batch 1 creates two governed artifacts:

1. This document (`docs/governance/CODEX_FIRST_CLASS_SCOPE.md`): the
   governance scope boundary for CFC-1 and any future Codex-first-class
   follow-on work.

2. `docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md`: the operational
   protocol for Hermes/Nefarious-to-Codex handoffs, Codex-only worktree
   isolation, evidence expectations, stop lines, transcript archival,
   and verifies-not-ratifies behavior.

Both artifacts are `governance/docs`-class and do not instantiate any
runtime surface, identity record, schema, or automation.

Delivery discoverability is provided by updates to
`docs/delivery/BACKLOG.md`, `KANBAN.md`, `DEPENDENCIES.md`, `README.md`,
and `RISK_REGISTER.md` within the allowed path manifest.

## 3. What Batch 1 does not authorize

Batch 1 explicitly does NOT authorize any of the following. Each item
below requires its own separately Source-ratified envelope before any
work may begin.

### 3.1 Codex identity record creation

No Codex identity record is created under Batch 1. A Codex identity
record is a privileged `identity`-class mutation per Feature 001 FR-008
and requires per-identity Source ratification. Any document that
resembles an identity record without explicit Source ratification is a
contract violation per FR-018.

### 3.2 Review-evidence schema creation

No review-evidence schema is created under Batch 1. Schema authoring is a
`schema`-class mutation and requires Source ratification of a schema
specification before any schema file is written. The Batch 2 evidence
reference in `docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md` §3
describes what a future schema must contain when it exists; it is not
the schema itself.

### 3.3 Architecture actor/tool matrix updates

No update is made to `docs/architecture/` actor/tool matrices under
Batch 1. Adding Codex as a named actor in the architecture is a
`governance`-class mutation that requires its own Source-ratified
envelope.

### 3.4 Codex authority expansion

Codex has no expanded authority under Batch 1. Specifically:

- Codex may not ratify any artifact. Source-only ratification is
  unchanged.
- Codex may not merge, deploy, or approve pull requests.
- Codex may not author tracked files outside a Codex-owned isolated
  worktree that is separately authorized for each batch.
- The verifies-not-ratifies invariant (Feature 001 FR-013; Feature 002
  FR-013) is not amended.

### 3.5 Codex ratification authority

Codex is never a ratifier. Review evidence authored by Codex may inform
Source, but it cannot substitute for Source ratification of any artifact
class. This invariant applies regardless of Codex review quality and
is unchanged by any CFC-1 batch landing.

### 3.6 Codex merge/deploy authority

Codex has no merge or deploy authority. Any PR authored by Codex must be
reviewed and ratified by Source before merge. Merge authorization and
deploy authorization remain Source-only per Feature 001 FR-008.

### 3.7 Provider/tool/model/host/account binding

No provider, tool, model, host installation, or account is bound under
Batch 1. Concrete runtime bindings are deployment-time overlay decisions
and are not selected upstream by this governance document. Any binding
attempt in this batch is a contract violation.

### 3.8 GitHub settings/rulesets/visibility mutation

No `.github/` content, branch protection settings, rulesets, repository
visibility, CODEOWNERS, or GitHub environments are mutated under Batch 1.
These remain privileged `governance`/`deploy`-class mutations requiring
their own Source-ratified envelopes.

### 3.9 Feature 005 dispatch automation

No dispatch automation, Hermes dispatcher implementation, or worktree
lifecycle automation is implemented under Batch 1. Feature 005 dispatch
automation is a separate privileged feature requiring its own
Source-ratified envelope under the `governance/code` mutation class.

## 4. Role and boundary restatements

### 4.1 Source-only ratification

Source is the sole ratifier for all privileged mutation classes per
Feature 001 FR-008. This includes `governance`, `identity`, `schema`,
`security`, `attestation`, `redaction`, and `deploy`. Batch 1 does not
delegate ratification authority to Codex, to any other AI actor, or to
any automated system.

### 4.2 Nefarious controller/reviewer/approver

Nefarious is the controller, reviewer, and approver for this batch and
for any CFC-1 Batch 2+ follow-on. Nefarious:

- Independently verifies the output of any implementer (including Claude
  Code) before reporting to Source for ratification.
- Does not author tracked files inside an implementer's envelope (per
  `docs/operations/CONTROLLER_BOUNDARY_POLICY.md` §d).
- Does not substitute their approval for Source ratification of
  privileged classes.

### 4.3 Claude Code as implementer (Batch 1)

Claude Code (Sonnet) acts as the visible implementer for this batch
under the Source-ratified Hermes envelope. Claude Code:

- Authors only the tracked paths named in the allowed path manifest.
- Does not stage, commit, push, create PRs, review, comment, merge,
  delete branches, or take any external action beyond local
  tracked-file authoring.
- Does not perform any action listed in §3.

### 4.4 Codex worktree isolation

When Codex acts in a future authorized batch:

- Codex may only act inside a Codex-owned isolated worktree that is
  separately authorized for that specific batch by Source.
- Codex may never write to the active Claude Code worktree or to the
  canonical main branch worktree.
- The one-driver-per-worktree rule from
  `docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md` applies: a worktree
  occupied by Codex is not simultaneously occupied by Claude Code or
  Nefarious for tracked-file authoring.
- Codex worktree isolation does not by itself constitute authorization;
  Source ratification of the specific batch envelope is still required.

## 5. Forward scope — what Batch 2+ addresses

The following items are explicitly deferred to later Source-ratified
CFC follow-on envelopes. Recording them here does not authorize them.
Review-evidence-schema framing follows the **Batch 2A §6.5 ratified
posture** captured in
[`./CODEX_ROLE_AND_AUTHORITY_DECISION.md`](./CODEX_ROLE_AND_AUTHORITY_DECISION.md):
review evidence is retained as a separate artifact class.
Architect-class artifacts authored by Codex are attested through the
ordinary attestation flow; review evidence remains the separate
artifact class any reviewer (Codex-as-reviewer or otherwise) may
author. The Batch 2A role/authority decision is **landed**; the Batch
2B architecture actor/tool matrix wording is **landed**; the Batch
2C identity record encoding decision is **landed** (Source ratified
eight §6 decisions via PR #29 / merge commit `66a8074`; see
[`./CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`](./CODEX_IDENTITY_RECORD_ENCODING_DECISION.md));
and the Codex identity record authoring envelope is **landed** — Source-ratified
privileged `identity`-class gate; single Codex identity record with
`role_category = architect` and `human_ratifier_roles = ["source"]`;
placeholder/unbound posture for `allowed_repositories`, `signing_policy`,
and `tenant_id`; storage paths under `tenants/creator-engine-substrate/codex/`;
no concrete provider/tool/model/host/account binding; PR #31 / merge commit
`78b57a4`; see [`../delivery/BACKLOG.md`](../delivery/BACKLOG.md) §e.14.
CFC follow-on Batch 2D.1 review-evidence schema is **landed** —
Source-ratified privileged `schema`-class envelope authoring
`schemas/review-evidence.schema.yaml`,
`templates/review-evidence.template.yaml`,
`docs/contracts/review-evidence.md`, the `review_evidence_schema`
validator check with unit and integration tests, and well-formed /
malformed examples; PR #34 / merge commit `e1f5ffc feat: add review
evidence schema contract (#34)` (PR head SHA `2a8fe0f`); see
[`../delivery/BACKLOG.md`](../delivery/BACKLOG.md) §e.15. CFC
follow-on Batch 2D.2 architect-evidence schema is **landed** —
Source-ratified privileged `schema`-class envelope authoring
`schemas/architect-evidence.schema.yaml`,
`templates/architect-evidence.template.yaml`,
`docs/contracts/architect-evidence.md`, the
`architect_evidence_schema` validator check with unit and
integration tests, and well-formed / malformed examples;
PR #36 / merge commit `51a2134 feat: add architect evidence
schema contract (#36)` (PR head SHA `451be39`); see
[`../delivery/BACKLOG.md`](../delivery/BACKLOG.md) §e.16.
Architect evidence is a separate artifact class from Batch 2D.1
review evidence; it preserves the Batch 2A §6.3 ratified
authority-boundary posture (architect parity is authoring parity,
not ratification/merge/deploy authority) and the Batch 2B
envelope-bound authority wording; it does not amend Batch 2D.1
review-evidence artifacts and does not authorize implementer-class
authoring. CFC follow-on Batch 2D.3 implementer-evidence schema
(`post-sprint-0/cfc-2d-3-implementer-evidence-schema`) is
**landed** — Source-ratified privileged `schema`-class envelope;
implementer evidence is a separate artifact class from Batch 2D.1
review evidence and Batch 2D.2 architect evidence; implementer-evidence
framing preserves the Batch 2A §6.3 ratified authority-boundary posture
(architect/implementer parity is authoring/execution parity, not
ratification/merge/deploy authority) and the Batch 2B
envelope-bound authority wording; it does not amend Batch 2D.1
review-evidence or Batch 2D.2 architect-evidence artifacts and
does not authorize ratification, merge, deploy, branch deletion,
branch protection mutation, live repository-settings change,
provider/tool/model/host/account binding, tenant binding, or
authority expansion. PR #38 / merge commit `01f21a5 feat: add
implementer evidence schema contract (#38)` (PR head SHA
`0b630be`); see
[`../delivery/BACKLOG.md`](../delivery/BACKLOG.md) §e.17.

| Deferred item | Expected class | Gate |
|---|---|---|
| CFC follow-on Batch 2A — Codex role/authority decision request | `governance` / `docs` | **Landed.** Source ratified Option C (per-batch architect/implementer authoring assignment) and the seven §6 decisions in [`./CODEX_ROLE_AND_AUTHORITY_DECISION.md`](./CODEX_ROLE_AND_AUTHORITY_DECISION.md). Batch 2A did not amend the seven-row FR-015 baseline authority-matrix rule. |
| CFC follow-on Batch 2B — Architecture actor/tool matrix update | `governance` / `docs` | **Landed.** Instantiates the Batch 2A §6.1 Option C role choice in [`../architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md) §a and §b.4. Authority remains envelope-bound, not personality-bound. |
| CFC follow-on Batch 2C — Codex identity record encoding decision request | `governance` / `docs` | **Landed.** Source ratified eight §6 decisions: Option A selected (single Codex identity record, baseline `role_category = architect`; Option C conservative fallback retained); `human_ratifier_roles = ["source"]`; placeholder/unbound posture for `allowed_repositories`, `signing_policy`, storage paths, and `tenant_id`; Batch 2D reaffirmed as downstream non-mutated by Batch 2C. PR #29 / merge commit `66a8074`; see [`./CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`](./CODEX_IDENTITY_RECORD_ENCODING_DECISION.md). |
| Codex identity record | `identity` (privileged) | **Landed.** Source-ratified CFC follow-on privileged `identity`-class envelope; single Codex identity record with `role_category = architect` and `human_ratifier_roles = ["source"]`; placeholder/unbound posture for `allowed_repositories`, `signing_policy`, and `tenant_id`; storage paths under `tenants/creator-engine-substrate/codex/`; no concrete provider/tool/model/host/account/tenant/repository bound. PR #31 / merge commit `78b57a4`; see [`../delivery/BACKLOG.md`](../delivery/BACKLOG.md) §e.14. |
| Review-evidence schema (Batch 2D.1) | `schema` (privileged) | Batch 2D.1 review-evidence schema is **landed.** Source-ratified privileged `schema`-class envelope; framing follows the Batch 2A §6.5 ratified posture (review evidence retained as a separate artifact class). PR #34 / merge commit `e1f5ffc` (PR head SHA `2a8fe0f`); see [`../delivery/BACKLOG.md`](../delivery/BACKLOG.md) §e.15. |
| Architect-evidence schema (Batch 2D.2) | `schema` (privileged) | Batch 2D.2 architect-evidence schema is **landed.** Source-ratified privileged `schema`-class envelope; architect evidence is a separate artifact class from Batch 2D.1 review evidence; framing preserves the Batch 2A §6.3 ratified authority-boundary posture (architect parity is authoring parity, not ratification/merge/deploy authority) and the Batch 2B envelope-bound authority wording. Does not amend Batch 2D.1 review-evidence artifacts and does not authorize implementer-class authoring. PR #36 / merge commit `51a2134` (PR head SHA `451be39`); see [`../delivery/BACKLOG.md`](../delivery/BACKLOG.md) §e.16. |
| Implementer-evidence schema (Batch 2D.3) | `schema` (privileged) | Batch 2D.3 implementer-evidence schema is **landed.** Source-ratified privileged `schema`-class envelope; implementer evidence is a separate artifact class from Batch 2D.1 review evidence and Batch 2D.2 architect evidence; framing preserves the Batch 2A §6.3 ratified authority-boundary posture and the Batch 2B envelope-bound authority wording; does not amend Batch 2D.1 or Batch 2D.2 artifacts and does not authorize ratification, merge, deploy, branch deletion, branch protection mutation, live repository-settings change, provider/tool/model/host/account binding, tenant binding, or authority expansion; reaffirmed as non-mutated by Batch 2C per [`./CODEX_IDENTITY_RECORD_ENCODING_DECISION.md`](./CODEX_IDENTITY_RECORD_ENCODING_DECISION.md) §6.8. PR #38 / merge commit `01f21a5` (PR head SHA `0b630be`); see [`../delivery/BACKLOG.md`](../delivery/BACKLOG.md) §e.17. |
| Provider/tool/model/host/account binding | deployment overlay | Source decision at binding time; binding posture remains placeholder/unbound per the Batch 2A §6.4 ratified posture and the Batch 2C §6.4 / §6.5 / §6.7 recommended posture |
| Codex authority expansion (ratification, merge, deploy) | Source decision | Not currently planned; Batch 2A §6.3 ratified that architect parity is authoring parity only and Batch 2C §4 / §7 inherits the boundary unmodified |
| Feature 005 dispatch automation | `governance` / `code` | Feature 005 spec ratified |

## 6. Cross-references

| Document | Relationship |
|---|---|
| `docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md` | Operational protocol companion; defines handoff format, worktree isolation mechanics, evidence expectations, and verifies-not-ratifies behavior. Do not duplicate governance scope from this document there. |
| `docs/delivery/BACKLOG.md` §e.10 | Backlog entry for `post-sprint-0/cfc-1-codex-first-class`. |
| `docs/delivery/DEPENDENCIES.md` §d.5 | Dependency edges: CFC-1 depends on Sprint 0 + post-Sprint-0 substrate; precedes Feature 004/CFC follow-on. |
| `docs/delivery/RISK_REGISTER.md` §c.13–§c.19 | CFC-1-specific risk controls. |
| `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md` | Source-only ratification authority; verifies-not-ratifies invariant. |
| `docs/governance/MUTATION_CLASS_MODEL.md` | Authoritative mutation class definitions; basis for all privilege determinations above. |
| `docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md` | One-driver-per-worktree rule and worktree naming conventions. |
| `docs/operations/CONTROLLER_BOUNDARY_POLICY.md` | Controller-verifies-never-authors rule; controller-seat-edit anti-pattern. |
| Feature 001 FR-007, FR-008, FR-013, FR-013a, FR-016 | Author/approver separation, privileged-class Source-only gate, verifies-not-ratifies, ratification flow. |
