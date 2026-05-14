# Definition of Ready (Delivery View)

**Status**: Sprint 0 Slices B, C, D, E, and F are complete on the
delivery view. B1 (markdown control-plane scaffold) and B2
(Definition of Ready, Definition of Done, dependency map, risk
register) landed previously; Slice C has since landed on the
canonical branch as PR #12 (`1cfb955 ci: add baseline governance
validation controls`); Slice D has since landed on the canonical
branch as commit `6058661 docs: define reviewer evidence gate for
Slice D`; Slice E subsequently landed on the canonical branch as
PR #14 / commit `3cb0266 docs: add Sprint 0 Slice E assignment
runtime protocol`; and Slice F has now landed on the canonical
branch as PR #16 / commit `cb7f94a docs: add Slice F release deploy
governance policy`. Part of the **minimum repo-native delivery
control plane** and **not a Jira clone**. Markdown-only by ratified
posture. Layered on top of, and subordinate to, the Feature 001
substrate. Live GitHub branch protection settings on the remote
repository remain a separate privileged future decision and are not
mutated by PR #12, PR #14, or PR #16.
Authorization-to-implement downstream feature work (Feature 003+
extension of the landed `.github/` baseline, Feature 004 reviewer-
identity instantiation, Feature 005 dispatcher / worktree
automation, Feature 006 release / deploy execution) remains
contingent on Source ratifying further per-batch privileged
envelopes; Slice F landing does not, by itself, authorize any
downstream consumption.

**Scope**: This document defines when a Creator Engine work item is
**Ready** to enter a Hermes-authored Assignment Envelope. It is the
delivery-view counterpart of the canonical readiness contract.

## a. Source-of-truth relationship

This Definition of Ready is a **delivery-view** readiness statement.
It is layered on top of the Feature 001 substrate contract and does
**not** amend it.

| Upstream source | Role |
|---|---|
| Feature 001 FR-013 / FR-013a | Canonical spec-lifecycle readiness rule. A spec MUST NOT advance from `draft` to `ready` without non-empty `scope`, `acceptance_criteria`, and `verification` fields. |
| [`docs/contracts/definition-of-ready.md`](../contracts/definition-of-ready.md) | Authoritative Feature 001 readiness contract. |
| Feature 002 §Assignment Envelope (FR-005 through FR-011) | Operating-model envelope schema and the rule that `/speckit-implement` is permitted only inside a Hermes-authored envelope. |
| [`./BACKLOG.md`](./BACKLOG.md) §a | Delivery-view status vocabulary, including `Ready`. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) | Delivery-view counterpart for completion. |
| [`./DEPENDENCIES.md`](./DEPENDENCIES.md) | Dependency map consumed by the "dependencies / blockers" criterion. |
| [`./RISK_REGISTER.md`](./RISK_REGISTER.md) | Standing risks that shape readiness checks (e.g., scope creep, privileged-class mis-classification). |
| Optional external trackers (Jira, Linear, GitHub Projects, etc.) | **Non-canonical** mirrors only. An external tracker entry MUST NOT, by itself, mark a repo work item as Ready. A fresh clone is sufficient to evaluate readiness; no external tracker credential or network state is required. |

Where this document and the Feature 001 contract disagree, the
Feature 001 contract controls until Source ratifies a correction. The
delivery view MUST NOT be used to amend, skip, or backfill the
Feature 001 lifecycle.

## b. Ready criteria

A work item is `Ready` (per [`./BACKLOG.md`](./BACKLOG.md) §a) only
when every criterion below is satisfied. Each criterion is named so
that a fresh clone reviewer can confirm the state from repository
artifacts alone.

### b.1 Stable backlog id

The work item appears in [`./BACKLOG.md`](./BACKLOG.md) with a stable
identifier (e.g., `sprint-0/slice-b/b2`, `feature-003`, `us3/a1`).
Identifiers are introduced in `BACKLOG.md` and never invented in an
envelope, a Kanban column, or an external tracker.

### b.2 Source of truth reference

The work item names its owning upstream source of truth: the Sprint 0
execution README, the roadmap, a ratified spec, or another upstream
artifact in the
[`./README.md`](./README.md) §c source-of-truth table. Items whose
upstream is not nameable MUST be flagged for Source ratification
before they advance past `Backlog`.

### b.3 Scope summary

A one-line scope summary exists on the backlog row, with any deferral
made explicit (e.g., "defer YAML sidecars to B3"). Open-ended or
vague scope ("improve delivery system") is not Ready; it returns to
`Backlog` for shaping.

### b.4 Allowed files or allowed path families

The work item names the file paths or path families it is permitted
to mutate (for `docs` work, typically a single subtree; for `code`
work, a named module). The envelope's `prohibited_surfaces` is the
complement of this list and is sized to make a scope audit
mechanical.

### b.5 Prohibited surfaces

The work item names the paths and surfaces that MUST NOT be mutated
under it. Privileged surfaces (`.github/`, `specs/`, `schemas/`,
`validators/`, `templates/`, `examples/`, `tenants/`, the canonical
documents under `docs/product/`, `docs/architecture/`,
`docs/governance/`, `docs/quality/`, `docs/devops/`, `docs/security/`,
`docs/contracts/`, repository settings, live GitHub / Jira / Linear /
GitHub Projects state) are listed explicitly when the item is even
adjacent to them.

### b.6 Anticipated mutation class

The work item declares the dominant Feature 001 baseline mutation
class expected to apply, drawn from the nine classes in
[`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md)
§a (`docs`, `code`, `schema`, `deploy`, `governance`, `identity`,
`security`, `attestation`, `redaction`). If multiple classes are
anticipated, each is listed; the most privileged class drives the
readiness gate.

### b.7 Dependencies / blockers

Every dependency named on the backlog row is at `Ratified` or `Done`,
per the rules in [`./DEPENDENCIES.md`](./DEPENDENCIES.md). Items
with unresolved dependencies remain `Backlog` or `Blocked`; they MUST
NOT be promoted to `Ready` until the named blocker clears.

### b.8 Validation commands or validation plan

The work item names the commands or evidence the consumer will
produce (e.g., validator runs, link checks, content smoke checks).
Validation that is "we'll figure it out at consume time" is not
Ready; the validation plan must be reconstructable from the backlog
row and the envelope.

### b.9 Owner role and ratifier role

The work item names the Feature 001 baseline role category expected
to author the work (`source`, `ratifier`, `reviewer`, `architect`,
`implementer`, `verifier`, `observer`) and the role category required
to ratify, per
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md).
Privileged classes resolve `ratifier role` to `source` or to a
`source`-delegated `ratifier` once delegation is ratified.

### b.10 External tracker boundary, if any

If the work item carries an external tracker reference (e.g.,
`ENG-1234`), the reference is marked **non-canonical** per
[`./README.md`](./README.md) §d. The external tracker entry MUST NOT
substitute for any repo-visible field. A fresh clone with no network
access and no tracker credential MUST be sufficient to evaluate the
readiness of every criterion above.

### b.11 Stop conditions

The work item names the conditions under which the consumer MUST
stop: the validation passes, the staged-file set matches the
declared allow-list, an authority conflict is detected, or a
prohibited surface is touched. Stop conditions are explicit in the
envelope; the readiness gate verifies that the backlog row can supply
them.

## c. Privileged-class rule

If the anticipated mutation class includes any of the six privileged
classes (`deploy`, `governance`, `identity`, `security`,
`attestation`, `redaction`) per Feature 001 FR-008, the readiness
gate has one additional, non-negotiable requirement:

> **Source ratification before implementation.**

Concretely:

1. The envelope itself MUST be Source-ratified before any consumer
   may begin work (Feature 002 FR-008).
2. CI passing, agent review text, an external tracker green check, or
   a "go ahead" message on a non-designated surface MUST NOT
   substitute for Source ratification.
3. If clearing a dependency requires a privileged mutation, the next
   step is a ratification request to Source, **not** the
   implementation (cf.
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.5).
4. Author/approver separation (Feature 001 FR-007) applies: the actor
   who will author the privileged mutation MUST NOT be its ratifier.

A privileged work item that has not cleared §c MUST remain `Backlog`,
`Blocked`, or `Deferred`. Promoting it to `Ready` is a contract
violation per Feature 001 FR-013 / FR-013a and an authority conflict
per Feature 002 FR-018.

## d. Worked example — B2 and Slice C readiness

This example illustrates the readiness gate at the time of the B2
batch and its post-merge reconciliation. It is non-normative; the
binding rules live in §b and §c. The example also distinguishes
**"Ready as the next candidate envelope"** (a delivery-view
bookkeeping state) from **"authorized to implement"** (which, for a
privileged class, additionally requires a Source-ratified envelope
per §c).

### d.1 `sprint-0/slice-b/b2` — Ready when authored; now `Done` on the delivery view

- **b.1 stable backlog id**: `sprint-0/slice-b/b2`. Present in
  [`./BACKLOG.md`](./BACKLOG.md) §c.2.2.
- **b.2 source of truth**: Sprint 0 execution README
  [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
  §5 (Slice B) and §4 (exit gates #2 and #3); the B1 README's deferred-file
  map.
- **b.3 scope summary**: author `DEFINITION_OF_READY.md`,
  `DEFINITION_OF_DONE.md`, `DEPENDENCIES.md`, `RISK_REGISTER.md` under
  `docs/delivery/`; markdown-only.
- **b.4 allowed paths**: `docs/delivery/DEFINITION_OF_READY.md`,
  `docs/delivery/DEFINITION_OF_DONE.md`,
  `docs/delivery/DEPENDENCIES.md`,
  `docs/delivery/RISK_REGISTER.md`, plus minimal updates to
  `docs/delivery/README.md`, `docs/delivery/BACKLOG.md`,
  `docs/delivery/KANBAN.md`, and
  `docs/delivery/NEXT_TASK_PROTOCOL.md` for discoverability and
  status coherence.
- **b.5 prohibited surfaces**: `.github/`, `.specify/`, `specs/`,
  `schemas/`, `validators/`, `templates/`, `examples/`, `tenants/`,
  the canonical documents under `docs/product/`,
  `docs/architecture/`, `docs/governance/`, `docs/quality/`,
  `docs/devops/`, `docs/security/`, `docs/contracts/`, repository
  settings, and any live GitHub / Jira / Linear / GitHub Projects
  mutation.
- **b.6 anticipated mutation class**: `docs` (non-privileged).
- **b.7 dependencies**: `sprint-0/slice-b/b1` is at `Ratified`
  (Source ratification of B1 recorded); the dependency rule "B1
  must reach `Ratified` or `Done`" is satisfied, so the edge is
  cleared for this batch.
- **b.8 validation**: Creator Engine validator's `check-examples` and
  `scan-no-limitless`, a content smoke check enumerating required
  phrases, a local markdown link check, and `git diff --check`.
- **b.9 roles**: owner role `implementer` (Claude Code under a
  Hermes-authored envelope); ratifier role `source`.
- **b.10 external tracker**: none. A fresh clone is sufficient.
- **b.11 stop conditions**: validation passes; staged-file set equals
  the eight allowed files; no prohibited-surface mutation; no
  commit / push / PR / merge.

The privileged-class rule in §c does NOT apply: the anticipated
mutation class is `docs`, not a privileged class. Readiness for B2
therefore turned on whether B1 had reached `Ratified` or `Done`. B2
was `Ready` once B1 cleared, the B2 envelope was consumed, and B2
has since landed on the canonical branch; both B1 and B2 are now
`Done` in [`./BACKLOG.md`](./BACKLOG.md) and
[`./KANBAN.md`](./KANBAN.md), so the parent `sprint-0/slice-b` is
also `Done` on the delivery view.

### d.2 `sprint-0/slice-c`, `sprint-0/slice-d`, `sprint-0/slice-e`, and `sprint-0/slice-f` — each was Ready as next candidate envelope and has since landed as `Done`

- **b.7 dependencies**: at the time Slice B landed,
  `sprint-0/slice-b` (the parent slice) reached `Done` on the
  delivery view, so the delivery-view dependency from Slice B to
  Slice C was cleared and Slice C was promoted to `Ready` as the
  next candidate envelope.
- **b.6 anticipated mutation class**: `governance` (privileged), with
  some `docs` for policy text, and possible `security` / `deploy`
  implications. Per §c, the privileged-class rule applied: being
  `Ready` as a delivery-view candidate was **not** authorization to
  implement. Source subsequently ratified a dedicated Slice C
  privileged envelope under Feature 001 FR-008 / FR-016 and Slice C
  landed on the canonical branch as PR #12
  (`1cfb955 ci: add baseline governance validation controls`),
  introducing the file-based `.github/` baseline only.
- **b.5 prohibited surfaces**: at consume time these included
  `.github/` for content B1 and B2 were not authorized to touch. The
  Slice C envelope was authorized to touch `.github/` (that was
  precisely its scope) but only inside a Source-ratified privileged
  envelope, and was not authorized to mutate live GitHub
  repository settings — those remain a separate privileged future
  decision regardless of Slice C landing.

The distinction — "Ready as next candidate envelope" vs.
"authorized to implement" — is the heart of the privileged-class
rule in §c. Slice D landed on the canonical branch as commit
`6058661 docs: define reviewer evidence gate for Slice D` under a
dedicated Source-ratified privileged `identity` envelope. Slice E
subsequently landed on the canonical branch as PR #14 / commit
`3cb0266 docs: add Sprint 0 Slice E assignment runtime protocol`,
also under a dedicated Source-ratified bounded `governance` /
`docs` envelope authoring the manual Assignment Envelope template
and worktree runtime protocol layer. Slice F has now landed on the
canonical branch as PR #16 / commit `cb7f94a docs: add Slice F
release deploy governance policy`, again under a dedicated
Source-ratified bounded docs-only `governance` / `docs` envelope
authoring the release / merge / deploy governance policy. The
Slice F row in [`./BACKLOG.md`](./BACKLOG.md) §c.6 is therefore
`Done` on the delivery view. The same "Ready as candidate vs.
authorized to implement" distinction now applies to any downstream
feature batch (e.g., Feature 003 extension, Feature 005 dispatcher
implementation, Feature 006 release / deploy execution): the
Sprint 0 delivery-view predecessor edges have cleared through to
F, but each downstream batch remains contingent on its own
Source-ratified privileged envelope. Slice C landing does not by
itself authorize any extension of the landed baseline (CODEOWNERS,
live branch protection settings, or Feature 003 instantiation);
Slice E landing does not by itself authorize any Feature 005 work;
Slice F landing does not by itself authorize Feature 006 release /
deploy execution; each remains a separately ratified envelope.

## e. Operating-procedure rules

1. Promoting an item to `Ready` is itself a delivery-view bookkeeping
   action. The promotion is recorded in [`./BACKLOG.md`](./BACKLOG.md)
   and reflected in [`./KANBAN.md`](./KANBAN.md). The promotion does
   not by itself advance the Feature 001 spec-status lifecycle; the
   spec wrapper sidecar continues to use Feature 001 FR-013a values.
2. A `Ready` item MAY be returned to `Backlog` (or marked `Blocked`)
   at any time if a §b criterion regresses (e.g., a dependency
   reverts to `In Progress` after a discovered defect).
3. Ambiguous or stale readiness (e.g., a row that references an
   artifact that no longer exists) is treated per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.3: refresh
   the backlog and escalate to Source. Do not improvise.
4. An external tracker entry MUST NOT, by itself, cause a status
   change here; if a tracker and the backlog disagree, the
   repo-visible backlog controls until Source ratifies an update
   (cf. [`./README.md`](./README.md) §d).
5. Instance-local facts (absolute filesystem paths, in-flight PR
   numbers, terminal pane identifiers, local session queues,
   secrets, credentials, tokens) MUST NOT enter this document or any
   readiness evidence captured under it.

## f. Acceptance posture for B2

This document satisfies the B2 envelope's Definition of Ready
requirements:

- Names this as a delivery-view DoR layered on top of Feature 001
  FR-013 / FR-013a.
- Enumerates the eleven Ready criteria (§b.1–§b.11) covering stable
  backlog id, source of truth, scope summary, allowed files / path
  families, prohibited surfaces, anticipated mutation class,
  dependencies / blockers, validation plan, owner and ratifier role,
  external tracker boundary, and stop conditions.
- Names the privileged-class rule (§c): privileged tasks require
  Source ratification before implementation.
- Provides a worked B2-vs-Slice-C example (§d) showing why
  `sprint-0/slice-b/b2` was `Ready` once B1 cleared (and has since
  landed as `Done`) and why `sprint-0/slice-c`, once Slice B was
  complete on the delivery view, was `Ready` as the next candidate
  envelope until Source ratified a dedicated Slice C privileged
  envelope; Slice C has since landed as PR #12, Slice D has since
  landed as commit `6058661`, Slice E has since landed as PR #14 /
  commit `3cb0266`, Slice F has now landed as PR #16 / commit
  `cb7f94a`, and the same "Ready as candidate vs. authorized to
  implement" distinction now applies to any downstream feature
  batch whose authorization-to-implement remains contingent on
  further Source-ratified envelopes.
