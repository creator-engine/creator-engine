# Definition of Done (Delivery View)

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
branch as PR #16 / commit `cb7f94a docs: add Slice F release
deploy governance policy`. Part of the **minimum repo-native
delivery control plane** and **not a Jira clone**. Markdown-only by
ratified posture. Layered on top of, and subordinate to, the
Feature 001 substrate.

**Scope**: This document defines when a Creator Engine work item is
**Done** on the delivery view. It is the delivery-view counterpart of
the canonical completion contract.

## a. Source-of-truth relationship

This Definition of Done is a **delivery-view** completion statement.
It is layered on top of the Feature 001 substrate contract and the
delivery-view status vocabulary in [`./BACKLOG.md`](./BACKLOG.md)
§a, and does **not** amend either.

| Upstream source | Role |
|---|---|
| Feature 001 FR-014 / FR-013a | Canonical Definition of Done: a spec MUST NOT enter `done` without an attestation record satisfying FR-004 and FR-008. The six-state lifecycle (`draft → ready → in_progress → verified → ratified → done`) is authoritative. The corresponding Feature 001 substrate contract lives at `specs/001-v0-1-governance-substrate/spec.md` and the contract surfaces under [`../contracts/`](../contracts/). |
| Feature 002 FR-013, FR-017 | Verifies-not-ratifies invariant: CI evidence is verification, never ratification; agent-authored review text is not ratification for privileged classes. |
| [`./BACKLOG.md`](./BACKLOG.md) §a | Delivery-view status `Done` semantics ("merged on the canonical branch with finalized attestation"). |
| [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) | Ten post-merge completion-report fields that a `Done` item MUST be reconstructable from. |
| [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) | The readiness gate; a `Done` item entered execution as `Ready`. |
| [`./DEPENDENCIES.md`](./DEPENDENCIES.md) | Dependency map; downstream items unblock only after this item is `Done` (or `Ratified` per the rule in §c). |
| [`./RISK_REGISTER.md`](./RISK_REGISTER.md) | Standing risks that bear on Done evidence (e.g., stale Kanban after merge, skipping Source ratification because CI passed). |
| Optional external trackers (Jira, Linear, GitHub Projects, etc.) | **Non-canonical** mirrors only. An external tracker status MUST NOT mark a repo work item Done. A fresh clone is sufficient to evaluate completion; no external tracker credential or network state is required. |

Where this document and the Feature 001 contract disagree, the
Feature 001 contract controls until Source ratifies a correction.

## b. Done criteria

A work item is `Done` (per [`./BACKLOG.md`](./BACKLOG.md) §a) only
when every criterion below is satisfied. Each criterion is named so
that a fresh clone reviewer can confirm the state from repository
artifacts alone.

### b.1 Implemented within the authorized scope

Every change shipped under the item is inside the envelope's
`allowed_mutation_classes`, inside the allowed files / path families
named at readiness, and outside the envelope's `prohibited_surfaces`.
Any deviation has been either reverted before merge or re-ratified by
Source under an explicit envelope amendment.

### b.2 Validation evidence captured

The validation commands or validation plan named at readiness
(per [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b.8)
have been run and their results recorded. Where Creator Engine
validator runs apply, their outputs are captured; where local-only
checks apply (link checks, smoke checks, `git diff --check`), their
outputs are captured. Skipped checks are explicitly named with a
rationale.

### b.3 Scope audit completed

A scope audit confirms that no prohibited surface was mutated. The
audit cites the surfaces the envelope declared as
`prohibited_surfaces` and names any unexpected paths in the diff with
their resolution (reverted; or reclassified under a ratified envelope
amendment). The audit is captured in the post-merge completion report
per [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.5.

### b.4 Independent review or equivalent evidence recorded (when applicable)

Where the work item is reviewable by an independent reviewer
identity, the review evidence is recorded. Codex (or an equivalent
reviewer identity once Feature 004 instantiates one) records review
findings under the schema named in the envelope. Until Feature 004
ratifies a review-evidence schema, the review evidence MAY be an
explicit "no independent reviewer applies for this batch" note inside
the post-merge report, captured by Hermes / Source — but only when
the batch's mutation class and scope make independent review
inapplicable; the note is not a substitute for review where review
is required.

**Review is not ratification.** Per Feature 002 FR-013, FR-017 and
Feature 001 FR-017, agent-authored review text MUST NOT count as
ratification for privileged classes regardless of how comprehensive
the review is.

### b.5 Source ratification recorded (privileged classes; Phase 1 integration)

For privileged-class work items (any of `deploy`, `governance`,
`identity`, `security`, `attestation`, `redaction` per Feature 001
FR-008), the ratification record cites Source as the ratifier and
satisfies Feature 001 FR-016 and FR-020a. For non-privileged-class
items during the current Phase 1 integration regime, Source
ratification of the canonical-branch integration is required even
when ratifier delegation is technically permitted, because Phase 1 is
the operational default in v0.1
([`../architecture/agentic-sdlc-operating-model.md`](../architecture/agentic-sdlc-operating-model.md)
§c). A Source-delegated `ratifier` becomes eligible for
non-privileged classes only once Source explicitly ratifies that
delegation.

A "go ahead" message on a surface that the ratification flow has not
designated as valid for the mutation class is NOT a ratification
record. Surface validity is policy-driven per
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
§c.

### b.6 PR/merge evidence captured (when applicable)

Where the work item produced a PR, the merge commit SHA, the PR
identifier visible in the canonical-branch commit subject, the
source branch, and the target branch are captured in the post-merge
report per [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.1.
Where the work item was integrated by a non-PR path (e.g., a
fast-forward from a Source-authored canonical-branch commit), the
mechanism is named explicitly and the SHA is captured.

In-flight PR numbers for work that has not merged MUST NOT appear in
this artifact or in any upstream artifact under this protocol; only
merged PR numbers in canonical-branch commit subjects MAY be cited
as historical evidence.

### b.7 Post-merge next-task report completed using all ten fields

A post-merge completion report exists for the item and uses **all
ten** fields from
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b: merge
identification, scope summary, validation evidence, governance
evidence, scope audit, documentation impact, deferred work,
readiness impact, immediate next-task recommendation, and cleanup
state. A report that omits any of the ten fields is incomplete per
[`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
§7, and the item is NOT `Done` until the report is complete.

### b.8 Backlog and Kanban updated after merge

[`./BACKLOG.md`](./BACKLOG.md) and [`./KANBAN.md`](./KANBAN.md)
reflect the merged state: the item is moved to `Done` (with durable
evidence cited — typically the canonical-branch merge commit
subject); downstream items have their dependency states refreshed;
the Kanban view is regenerated per
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d. An item is
NOT `Done` while either artifact still shows it in `In Progress` or
`Verified`.

### b.9 Cleanup state documented

The cleanup state is named per
[`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.10: branch
state on the canonical remote; worktree state; whether the feature
branch is to be deleted, retained, or requires Source approval
before deletion; whether any instance-local snapshot file needs an
update. Cleanup actions that mutate shared state (deleting remote
branches, force-pushes) MUST be ratified separately and MUST NOT
have been silently performed under this item's envelope.

## c. CI verifies; CI does not ratify

**CI verifies; CI does not ratify.**

This is a load-bearing invariant carried from Feature 002 FR-013 and
the verifies-not-ratifies rule at SDLC transition T17
([`../architecture/agentic-sdlc-operating-model.md`](../architecture/agentic-sdlc-operating-model.md)
§b). For the Definition of Done:

1. CI green status MAY be cited as **validation evidence** under
   §b.2 once a CI workflow is wired (currently deferred to Feature
   003 / Sprint 0 Slice C). CI red status MUST block `Done`.
2. CI green status MUST NOT, by itself, satisfy §b.5. A passing CI
   run is mechanical validation; it is not Source ratification.
3. A change to CI policy, branch protection, or `.github/` content is
   itself a privileged `governance` / `security` / `deploy`-class
   mutation per Feature 001 FR-008 and requires Source ratification.
4. The Slice C file-based `.github/` baseline (validation workflow
   `.github/workflows/validate.yml`, PR template
   `.github/pull_request_template.md`, branch protection policy
   `.github/BRANCH_PROTECTION_POLICY.md`) is already on the
   canonical branch as of PR #12 (`1cfb955`); §b.2 MAY cite that
   baseline's CI evidence where it applies. Further extension of
   the `.github/` baseline (live GitHub branch protection settings,
   CODEOWNERS, additional workflows, or any deeper instantiation)
   remains Feature 003 surface under a separately ratified
   privileged envelope. Where no applicable CI workflow has been
   wired for a given mutation class, §b.2 is satisfied by local
   validation evidence captured in the post-merge report; the
   report names the local-validation evidence relied upon per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.3.

## d. External tracker status cannot mark a repo work item Done

An external tracker entry (Jira, Linear, GitHub Projects, or any
future adapter ratified under Slice B4) is a **non-canonical** mirror
per [`./README.md`](./README.md) §d. The following are explicit
consequences for Done:

1. Closing an external tracker ticket does NOT mark the repo work
   item `Done`. The repo-visible artifacts in
   [`./BACKLOG.md`](./BACKLOG.md), [`./KANBAN.md`](./KANBAN.md), and
   the post-merge report are the authoritative completion record.
2. If the external tracker and the repo-visible backlog disagree
   about completion, the repo-visible backlog controls until Source
   ratifies an update.
3. An external tracker reference (e.g., `ENG-1234`) MAY appear on a
   backlog row as a non-canonical pointer; it MUST NOT be cited as
   the sole evidence for any §b criterion.
4. A fresh clone is sufficient to evaluate every §b criterion. No
   external tracker credential or network state is required for an
   auditor to determine whether a work item is `Done`.

## e. Operating-procedure rules

1. The `Done` status transition is mechanical bookkeeping over the
   evidence in §b. The transition does not by itself advance the
   Feature 001 spec-status lifecycle; the spec wrapper sidecar
   continues to use Feature 001 FR-013a values.
2. The Feature 001 lifecycle gate `ratified → done` (FR-013a) is the
   substrate-level mirror of §b. The delivery view MUST NOT mark a
   work item `Done` while the spec/plan/tasks sidecar shows it at
   `verified` or earlier; that would skip a Feature 001 lifecycle
   state and violate FR-027a.
3. A `Done` item MAY be reopened only by a Source-ratified amendment
   (a defect discovered post-merge that requires the item to revert
   to `In Progress` is itself a privileged change, since reopening a
   ratified work item is a governance-class mutation).
4. Ambiguous or stale completion evidence (e.g., a `Done` row
   pointing to a merge commit that no longer exists on the canonical
   branch) MUST be escalated to Source per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §c.3.
5. Instance-local facts (absolute filesystem paths, in-flight PR
   numbers, terminal pane identifiers, local session queues,
   secrets, credentials, tokens) MUST NOT enter the Done evidence or
   any upstream artifact under this protocol. Merged PR numbers in
   canonical-branch commit subjects MAY be cited as historical
   evidence.

## f. Acceptance posture for B2

This document satisfies the B2 envelope's Definition of Done
requirements:

- Names this as a delivery-view DoD layered on top of Feature 001
  FR-014 and on the delivery statuses in
  [`./BACKLOG.md`](./BACKLOG.md).
- Enumerates the nine Done criteria (§b.1–§b.9) covering scope
  conformance, validation evidence, scope audit, independent review
  evidence (when applicable), Source ratification (privileged
  classes and current Phase 1 integration), PR / merge evidence,
  the ten-field post-merge report, Backlog / Kanban refresh, and
  cleanup state.
- States explicitly that **CI verifies; CI does not ratify** (§c).
- States explicitly that external tracker status cannot mark a repo
  work item Done (§d).
