# Creator Engine Authority and Ratification Model

**Status**: Canonical. Authored under Sprint 0 Execution Slice A.

**Source-of-truth relationship**: SUMMARY. The authoritative source for
the authority matrix is the Feature 001 contract at
[`../contracts/authority-matrix.md`](../contracts/authority-matrix.md)
(schema: `schemas/authority-matrix.schema.yaml`; baseline data:
`docs/contracts/authority-matrix.yml`). The authoritative ratification
flow lives at the Feature 001 contract
`docs/contracts/ratification-flow.md` (deferred per Feature 001 sub-
batch B); the operating-model layer references it without redefining
it. This document SUMMARIZES and LINKS; it does not override.

## a. Summary of the Feature 001 authority matrix (FR-015)

The substrate ships exactly seven baseline role-category rows — one per
`role_category` enum value (Source-approved 2026-05-10). Tenant-
specific role names live in `tenants/<name>/authority-matrix-overlay.yml`
and never in the substrate baseline.

| Role category | Description (per Feature 001 contract) |
|---|---|
| `source` | Project owner/operator with authority to approve governance direction and ratify privileged mutations. |
| `ratifier` | Human or named role authorized by Source to accept a mutation after reviewing its evidence. |
| `reviewer` | Provides review/advisory text on artifacts under review; does not author the mutation under review. |
| `architect` | Designs the spec/plan/contract for a feature; authors generic contract documents and schemas. |
| `implementer` | Authors the code, schema, or docs that fulfills an approved spec/plan/tasks triple. |
| `verifier` | Authors verification artifacts (tests, validators, verification scripts). |
| `observer` | Writes observation artifacts (notes, handoffs); least-privilege role. |

Each row contains:

- `allowed_instruction_sources` — kinds of artifact or directive the
  role may take work from (e.g., `spec`, `plan`, `tasks`,
  `source_directive`, `ratification_record`).
- `allowed_mutation_classes` — mutation classes the role may author
  work in; together the seven rows cover every baseline class
  (`docs`, `code`, `schema`, `deploy`, `governance`, `identity`,
  `security`, `attestation`, `redaction`).
- `required_ratifier_role` — one of the seven role categories. For
  privileged-class rows, MUST be `source` or `ratifier`
  (human-eligible).
- `allowed_communication_surfaces` — named surfaces on which this role
  may operate (e.g., `repo_pr`, `repo_review`, `repo_commit_message`,
  `repo_issue`, `repo_attestation_record`, `repo_ratification_record`).
- `required_audit_artifacts` — artifacts this role MUST produce or be
  named in (e.g., `attestation_record`, `ratification_record`).

The actor/tool ownership matrix in Feature 002 (see
[`../architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md)
§a and the spec at
`specs/002-canonical-docs-and-operating-model/spec.md` §Actor/Tool
Ownership Matrix) attaches concrete operating-model actors (`Source`,
`Nefarious/Hermes`, `Claude Code`, `Codex`, future `QA agent`,
`security agent`, `release agent`, `CI`, `GitHub`) to these role
categories. The Feature 002 matrix supplements the Feature 001 contract
with operating-model presence categories; it does not override the
baseline matrix.

### a.1 Operator display-label / compatibility note (per ADR-0002)

`docs/adr/ADR-0002-operator-terminology-reconciliation.md` ratifies
the product-facing terminology policy. This note is the compatibility
/ display-label record next to the role-category table; ADR-0002 is
the controlling authority and this note summarizes without
redefining. The note changes no schema name, no enum value, and no
authority semantic.

- **`role_category: source` is preserved** as the v1 machine value
  for the apex authority through the entire v1.x line. The same
  preservation applies to other v1 contract fields that encode the
  apex authority (e.g., `required_ratifier_role: source`,
  `merged_by_role: source`, `grant_authority: source`).
- **The product-facing display label** rendered for the v1 machine
  value `source` is **`Operator`** in new product-facing prose
  (docs, prompts, completion reports, CLI/runtime text, examples,
  templates governed by the in-scope path-glob list in ADR-0002 §7).
- **`source` enum compatibility is preserved through v1.x.** No
  machine enum hard-rename occurs in v1.x; removal or hard
  deprecation is deferred to a future v2/schema-version decision.
- **Human / agent / CI ratification invariants are unchanged.** The
  ratifier taxonomy in §b, the privileged mutation classes in §c,
  and the review-vs-ratification invariants in §d are unaffected by
  the display-label change. The acting party named `Source` in this
  document and named `Operator` in new product-facing prose denote
  the same authority role.
- **Agents, CI, GitHub, fan-in, and reviewers still do not ratify.**
  The two-tier author/approver separation rule applies to every
  ratification regardless of which display label is in use.
- **Ratification-line compatibility.** Canonical-attestation parsers
  MUST accept both `Operator ratifies prompt:` and `Source ratifies
  prompt:` for the entire v1.x line. Only the canonical emit form
  changes to `Operator ratifies prompt:` after the migration lands.
  Removal of legacy acceptance is deferred to v2/schema-version.

## b. Ratifier role taxonomy

Two role categories may ratify under v0.1:

- **`source`** — the apex ratifier for every privileged mutation
  class (FR-008). Source ratification is the human anchor and is not
  subject to Phase 2 autonomy expansion.
- **`ratifier`** — a human or named role authorized by Source to
  accept a mutation after reviewing its evidence. A `ratifier`
  ratifies non-privileged classes; for privileged classes the
  `required_ratifier_role` MUST resolve to `source` or to a
  human-eligible `ratifier` role per the Feature 001 contract's
  Reading A strict rule.

No other role category ratifies. Specifically:

- **`reviewer`** writes review evidence; review text is NOT
  ratification for privileged classes (Feature 001 FR-017; Feature
  002 FR-013).
- **`architect`**, **`implementer`**, **`verifier`**, and
  **`observer`** never ratify.
- **CI**, **agents**, and **GitHub** never ratify (Feature 002
  FR-013).

The author/approver separation rule applies to every ratification:
the actor who authored a mutation MUST NOT be the approving reviewer
or the ratifier of that same mutation (Feature 001 FR-007).

## c. Privileged mutation classes (Feature 001 FR-008)

The six privileged classes that require explicit human ratification:

- `deploy`
- `governance`
- `identity`
- `security`
- `attestation`
- `redaction`

These classes MUST set `human_ratification_required: true` in their
taxonomy entry and MUST resolve `required_ratifier_role` to `source`
or `ratifier` in every authority-matrix row that touches them.

Summary by class (the authoritative effects of ratification live in
the Feature 001 ratification-flow contract; this is a navigational
table):

| Class | Typical ratification surface | Author/approver separation note |
|---|---|---|
| `deploy` | `repo_ratification_record` + Source-approved deploy gate | Hermes audits; never ratifies its own work. |
| `governance` | `repo_ratification_record` + commit message on Source-approved commits | Source ratifies; cannot ratify Source's own authored mutations. |
| `identity` | `repo_ratification_record` | Identity records are Source-ratified before instantiation. |
| `security` | `repo_ratification_record` | Security agent (Feature 004 deferred) never ratifies the `security` class. |
| `attestation` | `repo_ratification_record` | Attestation gate weakening is Source-only. |
| `redaction` | `repo_ratification_record` | Redaction approver MUST NOT be the author of the underlying tenant artifact (Feature 001 FR-021). |

The "Typical ratification surface" column is illustrative. The full
ratification flow (which surfaces count as *valid* ratification
surfaces per mutation class) is defined in the Feature 001
`docs/contracts/ratification-flow.md` contract (sub-batch B). Three
policy claims from
[`../contracts/authority-matrix.md`](../contracts/authority-matrix.md)
§Ratification flow are restated here for orientation:

1. **Surface validity is policy-driven.** A surface in
   `allowed_communication_surfaces` may carry ratification artifacts;
   whether it counts as a valid ratification surface for a given
   mutation class is governed by the ratification-flow document and
   the tenant `tenants/<name>/ratification-flow.yml` overlay.
2. **Agent-authored review text is not ratification for privileged
   classes.** For privileged classes, agent-authored text is never
   ratification regardless of surface.
3. **A "go ahead" message is not merge authorization by itself.** A
   "go ahead" on a surface that the ratification flow has not
   designated as valid for the relevant class does not authorize
   merge, deploy, publish, or any other reserved-restricted action.

## d. Review-vs-ratification distinction (invariants)

Feature 002 FR-013 and FR-017 anchor two invariants:

- **CI verifies but does not ratify.** CI output (test logs,
  validator outputs, build artifacts) becomes attestation evidence;
  it never becomes a ratification record.
- **Agent-authored review text MUST NOT count as ratification for
  privileged mutation classes.** For non-privileged classes, agent
  review text MAY be recorded as review evidence per the Feature 001
  authority matrix, but it remains distinct from ratification and
  never substitutes for it.

These invariants combine with author/approver separation to make
single-actor approval impossible for privileged classes regardless of
how compelling the agent's review text is, how green CI runs, or how
emphatic any "go ahead" message reads.

## e. Escalation policy

Authority conflicts (per Feature 002 FR-018) hard-stop work. The
escalation path is uniform:

1. The detecting actor (Hermes audit, validator, CI evidence, scope
   audit, or any reviewer) records the conflict against the relevant
   SDLC transition and the offending change.
2. Work HALTS. The agent MUST NOT continue, revert, or rebase to
   conceal the conflict.
3. The case is escalated to Source for ratification.
4. Source EITHER ratifies the change as an explicit amendment (with
   the change required to be reverted if not ratified) OR directs the
   change to be reverted.
5. The ratification record (or revert record) is committed before any
   downstream SDLC transition advances.

Authority conflicts include (without limitation) agent attempts to
mutate identity, the authority matrix, `.github/`, redaction gate, CI
or deploy settings, ratification semantics, or any other privileged
surface absent explicit Source ratification; or `/speckit-implement`
invocation outside a Hermes-authored envelope (Feature 002 FR-009).

## f. SDLC transition → ratifier role link table

The full SDLC Transition Matrix lives in
[`../architecture/agentic-sdlc-operating-model.md`](../architecture/agentic-sdlc-operating-model.md)
§b. Below is the navigational link table from each transition that
requires ratification or operates on a privileged class to its
ratifier role.

| Transition | From → To | Ratifier role / decision | Notes |
|---|---|---|---|
| T3 | PRD Drafted → PRD Ratified | `source` (governance class — privileged) | Phase 1 only. |
| T5 | Architecture Drafted → Architecture Ratified | `source` (governance class — privileged) | Phase 1 only. |
| T10 | Tasks Generated → Batch Approved | `source` for privileged-class batches; `source`-delegated `ratifier` for non-privileged classes once delegation ratified | Phase 1 today; non-privileged Phase 2-eligible target. |
| T11 | Batch Approved → Agent Assigned | Hermes drafts; no ratification | Envelope authoring per FR-005. |
| T15 | Local Validation Complete → Attestation Drafted | Hermes drafts; `source` ratifies the attestation gate (`attestation` class — privileged) | Phase 1 only. |
| T16 | Attestation Drafted → Independent Review Complete | Codex review evidence; never ratification for privileged classes | Review schema deferred Feature 004. |
| T17 | Independent Review Complete → CI Evidence Complete | CI evidence; never ratification | Verifies-not-ratifies invariant (FR-013). |
| T18 | CI Evidence Complete → Scope Audit Complete | Hermes scope audit | Phase 1 today; Phase 2-eligible target for non-privileged classes. |
| T19 | Scope Audit Complete → Ratification Complete | `source` for privileged; `source`-delegated `ratifier` for non-privileged (once delegation ratified) | Ratification record per Feature 001 FR-016, FR-020a. |
| T20 | Ratification Complete → Merge Approved | `source` (merge authorization) | Hermes may execute merge mechanics only when Source authorization is recorded. |
| T21 | Merge Approved → Release Candidate Created | Hermes under Source authorization (until Feature 006 instantiates the release agent) | RC tagging policy. |
| T22 | Release Candidate Created → Deployment Approved | `source` (`deploy` class — privileged) | Phase 1 only. |
| T23 | Deployment Approved → Deployment Complete | future release agent executes; ratification belongs to Source (`deploy` class) | Feature 006 deferred. |
| T24 | Deployment Complete → Post-release Evidence Recorded | future release agent records; Hermes audits | Feature 006 deferred. |

Non-listed transitions (T1, T2, T4, T6–T9, T12–T14) are Phase 1 today
and do not require ratification per se; they are gated by Definition
of Ready, Definition of Done, envelope authoring, or local-validation
evidence. The Feature 001 lifecycle gate
`verified → ratified` (FR-013a) is the lifecycle-level mirror of
T19/T20.

## Acceptance posture for this document

This AUTHORITY_AND_RATIFICATION_MODEL.md satisfies Feature 002
Canonical Document Specification #10: the privileged-classes list
matches Feature 001 FR-006/FR-008 exactly; no role definition
overrides the Feature 001 authority matrix; the SDLC transition →
ratifier link table covers every transition that requires
ratification; the document SUMMARIZES rather than redefines.
