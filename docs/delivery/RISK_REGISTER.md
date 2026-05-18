# Sprint 0 Risk Register

**Status**: Sprint 0 Slices A–F complete on the delivery view;
post-Sprint-0 substrate (PRs #20–#23) has also landed on the
canonical branch. CFC-1 (`post-sprint-0/cfc-1-codex-first-class`)
specific risk controls have been added as §c.13–§c.19; CFC-1 Batch 1
has since landed on the canonical branch as PR #25 / `30a3e8c`. CFC
follow-on Batches 2A (PR #27 / `6b51882`), 2B (PR #28 / `c06a3e7`),
and 2C (PR #29 / `66a8074`) have all landed; Source ratified eight §6
decisions in Batch 2C. The Codex identity record authoring envelope has
since landed on the canonical branch as PR #31 / merge commit `78b57a4`;
see [`./BACKLOG.md`](./BACKLOG.md) §e.14. CFC follow-on Batch 2D.1
review-evidence schema has since landed on the canonical branch as
PR #34 / merge commit `e1f5ffc feat: add review evidence schema
contract (#34)` (PR head SHA `2a8fe0f`); see
[`./BACKLOG.md`](./BACKLOG.md) §e.15. CFC follow-on Batch 2D.2
architect-evidence schema
(`post-sprint-0/cfc-2d-2-architect-evidence-schema`) has since
landed on the canonical branch as PR #36 / merge commit `51a2134
feat: add architect evidence schema contract (#36)` (PR head SHA
`451be39`); see [`./BACKLOG.md`](./BACKLOG.md) §e.16. CFC follow-on
Batch 2D.3 implementer-evidence schema
(`post-sprint-0/cfc-2d-3-implementer-evidence-schema`) has since
landed on the canonical branch as PR #38 / merge commit `01f21a5
feat: add implementer evidence schema contract (#38)` (PR head SHA
`0b630be`); see [`./BACKLOG.md`](./BACKLOG.md) §e.17. Gate 2 Lane A
has since landed on the canonical branch as PR #40 / merge commit
`a63304a docs: add parallel pair rehearsal runbook (#40)`; see
[`./BACKLOG.md`](./BACKLOG.md) §e.18. Gate 2 Lane B has since landed
on the canonical branch as PR #41 / merge commit `8dd18a0 docs: add
external contributor intake boundary (#41)`; see
[`./BACKLOG.md`](./BACKLOG.md) §e.19. PR #42 / merge commit `921d46d
docs: reconcile gate 2 delivery ledgers (#42)` landed the Gate 2
delivery-ledger reconciliation; it is a reconciliation event and does
not require a new backlog row. The delivery view now reflects
canonical main at commit `921d46d8ef7e489f16158fe6b2f85f96f8bbbcec`.
A new post-Sprint-0 substrate parent
`post-sprint-0/root-worktree-lifecycle` has since been added with
four child gates (audit `Done`; policy/docs current in progress;
checks/preflight deferred; current-root reconciliation deferred);
see [`./BACKLOG.md`](./BACKLOG.md) §e.20.
`post-sprint-0/root-worktree-lifecycle/policy-docs-current` is the
interposed policy/docs gate that runs next after this delivery-header
reconciliation. Public-readiness continuation remains blocked **only**
until that policy/docs child gate lands; the deferred
`post-sprint-0/root-worktree-lifecycle/checks-preflight` and
`post-sprint-0/root-worktree-lifecycle/current-root-reconciliation`
gates remain later separately Source-ratified gates and are not on
the public-readiness critical path. Repository visibility /
public-readiness remain separately Source-ratified and
unimplemented. Part of the **minimum repo-native delivery
control plane** and **not a Jira clone**. Markdown-only by ratified
posture. Layered on top of, and subordinate to, the Feature 001
substrate.

**Scope**: This register names the standing risks to Sprint 0
execution and the immediate post-Sprint-0 follow-on work. It is a
risk-management view; it does not introduce new work items, and it
does not amend the contracts cited under each mitigation.

## a. Source-of-truth relationship

This register is a **delivery-view** artifact. It is layered on top
of the contracts and policies named under each mitigation and does
**not** redefine them.

| Upstream source | Role |
|---|---|
| [`./README.md`](./README.md) | Anti-Jira-clone scope statement and tracker boundary; basis for R-001 and R-002. |
| [`./BACKLOG.md`](./BACKLOG.md), [`./KANBAN.md`](./KANBAN.md) | Delivery-view status vocabulary and current state; basis for R-004 and R-005. |
| [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) | Ten post-merge fields and update procedure; basis for R-004. |
| [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md), [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) | Privileged-class gates; basis for R-003 and R-007. |
| [`./DEPENDENCIES.md`](./DEPENDENCIES.md) | Dependency map; basis for R-009 and R-010. |
| Feature 001 substrate (FR-006, FR-008, FR-013, FR-013a, FR-014, FR-016, FR-027a, etc.) | Authoritative substrate contracts. |
| Feature 002 spec at `specs/002-canonical-docs-and-operating-model/spec.md` | Operating-model invariants, including verifies-not-ratifies (FR-013) and the conflict taxonomy (FR-017/FR-018). |
| [`../operations/session-continuity-protocol.md`](../operations/session-continuity-protocol.md) | Instance-local-vs-upstream split; basis for R-006. |
| Optional external trackers (Jira, Linear, GitHub Projects, etc.) | **Non-canonical** mirrors only. Tracker entries are advisory; basis for R-002 and R-006. |
| Workflow-hardening protocol set ([`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md), [`../operations/NO_COPY_PASTE_PATTERN.md`](../operations/NO_COPY_PASTE_PATTERN.md), [`../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`](../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md), [`../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md`](../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md)) | Post-Sprint-0 substrate; durable evidence landed under PR #22 / `d892cd3` and PR #23 / `3dc45a1`. Upstream source for R-011 (§c.11) and R-012 (§c.12) mitigations. |

A fresh clone is sufficient to evaluate this register. No external
tracker credential or network state is required.

## b. Likelihood / impact scales

For consistency across rows, this register uses simple ordinal
scales.

| Scale | Values |
|---|---|
| Likelihood | `Low`, `Medium`, `High` |
| Impact | `Low`, `Medium`, `High`, `Severe` (defined as: Severe blocks Sprint 0 exit or corrupts the substrate) |

Owners are named by Feature 001 role category
([`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md))
rather than by specific named operators, so the register survives
operator changes.

## c. Risks

### c.1 R-001 — Scope creep into building a Jira clone

- **id**: `R-001`
- **description**: The delivery control plane under `docs/delivery/`
  is repeatedly expanded toward dashboards, custom workflow engines,
  burndowns, notification routing, sprint ceremonies, or any other
  surface of an enterprise issue tracker. Each individual addition
  is locally reasonable; together they reproduce a Jira clone
  inside the repository and consume Sprint 0 capacity that should be
  spent on Slice C–F policy authoring.
- **likelihood**: `Medium`.
- **impact**: `High`. Drains Sprint 0 capacity; pollutes the
  delivery view with non-governance surfaces.
- **mitigation**:
  1. The B1 README's anti-Jira-clone statement
     ([`./README.md`](./README.md) §b) is the binding scope
     ceiling. Each new file under `docs/delivery/` MUST cite which
     governance question it answers; if no governance question is
     answerable from the file alone, the file is out of scope.
  2. The eight current `docs/delivery/` files plus the deferred B3 /
     B4 successors in [`./DEPENDENCIES.md`](./DEPENDENCIES.md) §c
     are the canonical surface for Sprint 0 exit; expansions are a
     ratified amendment.
  3. The post-merge next-task report
     ([`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.6)
     names any new `docs/delivery/` artifact and the governance
     question it answers, surfacing creep at merge time.
- **trigger / early warning**: A proposed envelope adds files to
  `docs/delivery/` whose names mirror enterprise-tracker surfaces
  (dashboards, sprint reports, notifications, audit dashboards,
  custom workflow definitions). A backlog row whose scope summary
  describes a tracker-product feature rather than a governance gate.
- **owner role**: `source` (scope authority); `architect` (proposer
  of new control-plane surfaces).
- **current status**: Open; mitigation active under Sprint 0 Slice
  B.

### c.2 R-002 — External tracker canonicalization / SaaS dependency

- **id**: `R-002`
- **description**: A future operator routes work through an external
  tracker (Jira / Linear / GitHub Projects / a custom SaaS) and the
  external entry becomes the *de facto* source of truth, eroding the
  fresh-clone requirement. Source ratification, completion claims,
  or dependency edges begin to live only in the tracker.
- **likelihood**: `Medium`.
- **impact**: `Severe`. Breaks PR-NF-002 (repo-native v0.1) and the
  Sprint 0 exit gate #2 requirement that a fresh clone identify the
  next task without external state.
- **mitigation**:
  1. The tracker boundary in [`./README.md`](./README.md) §d names
     external tracker entries as **non-canonical** and forbids them
     from substituting for any repo-visible artifact.
  2. [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b.10
     and [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §d
     explicitly prohibit using a tracker entry to mark an item
     `Ready` or `Done`.
  3. [`./DEPENDENCIES.md`](./DEPENDENCIES.md) §i records that
     external tracker dependency claims are advisory unless
     mirrored in the repo-visible backlog.
  4. Any adapter design is gated by `sprint-0/slice-b/b4`, which is
     `Deferred` and requires Source ratification before any
     implementation work begins.
- **trigger / early warning**: A merge report cites a tracker entry
  as ratification evidence; a backlog row cites only an
  `external_tracker_ref` as the source of truth; an envelope
  consumes a tracker URL where it should consume a repo-visible
  spec / backlog id.
- **owner role**: `source` (boundary authority); `architect`
  (designs of any future B4 adapter).
- **current status**: Open; mitigation active. No adapter is
  authorized in Sprint 0.

### c.3 R-003 — Skipping Source ratification because CI or an agent review passes

- **id**: `R-003`
- **description**: A privileged-class mutation (any of `deploy`,
  `governance`, `identity`, `security`, `attestation`, `redaction`)
  is treated as ratified because CI is green, because Codex (or a
  future review agent) wrote a favorable review, or because a "go
  ahead" message appeared on a non-designated surface. The
  verifies-not-ratifies invariant collapses.
- **likelihood**: `Medium`. Strong correlation between green CI and
  perceived authority creates pressure to skip the explicit
  ratification step.
- **impact**: `Severe`. Violates Feature 001 FR-008, FR-017, and
  Feature 002 FR-013; corrupts the substrate.
- **mitigation**:
  1. [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §c states
     **CI verifies; CI does not ratify** as a load-bearing
     invariant.
  2. [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §c
     requires Source ratification before implementation for any
     privileged-class envelope.
  3. [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
     §c restates that agent-authored review text is not
     ratification for privileged classes and that a "go ahead" on a
     non-designated surface is not merge authorization.
  4. The post-merge governance evidence field
     ([`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.4)
     names the ratification record per Feature 001 FR-008 / FR-016
     for every privileged mutation.
- **trigger / early warning**: A merge report under a privileged
  envelope cites CI status or an agent review as governance
  evidence without a separate `repo_ratification_record`. A
  ratification record's signer equals the mutation's author
  (Feature 001 FR-007 violation).
- **owner role**: `source` (sole ratifier for privileged classes);
  `ratifier` (where Source has delegated for non-privileged
  classes).
- **current status**: Open; mitigation active across DoR, DoD,
  governance docs, and the next-task protocol.

### c.4 R-004 — Stale backlog or Kanban after a merge

- **id**: `R-004`
- **description**: A merge lands on the canonical branch but
  [`./BACKLOG.md`](./BACKLOG.md) and / or
  [`./KANBAN.md`](./KANBAN.md) are not updated to reflect the new
  state. Subsequent envelopes are authored against a stale next-task
  recommendation. The fresh-clone reviewer cannot identify the
  current state.
- **likelihood**: `Medium`. Merge-time bookkeeping is easy to
  forget when CI runs are long or post-merge attention shifts.
- **impact**: `High`. Breaks Sprint 0 exit gate #2's "answer 'what
  is next?' after every merge" requirement; cascades into mis-scoped
  envelopes.
- **mitigation**:
  1. [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d.1 and
     §d.2 require `BACKLOG.md` and `KANBAN.md` to be refreshed
     under every post-merge report.
  2. [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.8
     makes the refresh a Done criterion. An item is NOT `Done`
     while either artifact still shows it in `In Progress` or
     `Verified`.
  3. The post-merge documentation-impact field
     ([`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.6)
     names every changed `docs/delivery/` artifact, surfacing
     missing refreshes during the report's own authoring.
- **trigger / early warning**: A backlog row shows `In Progress`
  for an id whose canonical-branch evidence column already cites a
  merge commit subject. A Kanban column shows a different state
  than the backlog row for the same id. A next-task recommendation
  points to a work item that was already merged.
- **owner role**: `implementer` (merge author / Hermes drafts the
  report); `reviewer` (catches missed refresh).
- **current status**: Open; mitigation active under the post-merge
  update procedure.

### c.5 R-005 — Status vocabulary confusion between delivery-view statuses and Feature 001 lifecycle statuses

- **id**: `R-005`
- **description**: The eight delivery-view statuses (`Backlog`,
  `Ready`, `In Progress`, `Verified`, `Ratified`, `Done`,
  `Deferred`, `Blocked`) and the six Feature 001 lifecycle states
  (`draft → ready → in_progress → verified → ratified → done`,
  FR-013a) are conflated. The delivery view is used to skip,
  backfill, or amend the substrate lifecycle.
- **likelihood**: `Medium`. The vocabularies share several names
  (`Ready`, `In Progress`, `Verified`, `Ratified`, `Done`), inviting
  the assumption that they are the same.
- **impact**: `High`. Violates Feature 001 FR-027a; corrupts the
  substrate audit trail.
- **mitigation**:
  1. [`./BACKLOG.md`](./BACKLOG.md) §a and
     [`./KANBAN.md`](./KANBAN.md) §a explicitly state that the
     delivery-view statuses are layered on, and do not amend, the
     Feature 001 lifecycle.
  2. [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §e and
     [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §e
     prohibit using a delivery-view transition to advance the
     spec-status lifecycle.
  3. The post-merge update procedure
     ([`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §d.4)
     requires confirming that the Feature 001 spec-status values on
     the affected spec(s) match the delivery-view statuses applied.
- **trigger / early warning**: A spec wrapper sidecar shows a
  Feature 001 status that the delivery view "promoted" past, with
  no corresponding `/speckit-` lifecycle transition recorded. A
  merge report uses delivery-view vocabulary as if it were
  authoritative over the spec lifecycle.
- **owner role**: `architect` (operating-model authority);
  `verifier` (validator surfaces FR-027a violations).
- **current status**: Open; mitigation active across BACKLOG, KANBAN,
  DoR, DoD, and the next-task protocol.

### c.6 R-006 — Instance-local facts leaking into upstream docs

- **id**: `R-006`
- **description**: Absolute filesystem paths, terminal pane
  identifiers, in-flight PR numbers, local session queues, secrets,
  credentials, tokens, or other instance-local facts are written
  into upstream artifacts under `docs/`, `specs/`,
  `.specify/memory/`, or any tracked file. The upstream tree picks
  up dependencies on a specific operator's environment.
- **likelihood**: `Medium`. Convenience favors pasting whatever is
  in the current shell or window title into a doc; the prohibition
  is easy to forget when drafting reports under time pressure.
- **impact**: `High`. Breaks the fresh-clone requirement and the
  tenant-agnosticism principle (constitution Principle IX). May
  also leak secrets.
- **mitigation**:
  1. [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §e
     prohibits instance-local facts in any `docs/delivery/` artifact
     and lists the specific banned categories.
  2. [`./BACKLOG.md`](./BACKLOG.md) §f and
     [`./KANBAN.md`](./KANBAN.md) §d carry the same prohibition.
  3. [`../operations/session-continuity-protocol.md`](../operations/session-continuity-protocol.md)
     defines the instance-local-vs-upstream split: instance-local
     state belongs in an ignored snapshot file, not in the tracked
     tree.
  4. The Creator Engine validator's `scan-no-limitless` check and
     the B2 content smoke check explicitly reject named banned
     phrases (e.g., absolute home paths, tracker tokens).
- **trigger / early warning**: A grep of the tracked tree for
  banned tokens returns hits; a merge report's evidence cites a
  local shell prompt; a backlog row references an in-flight PR
  number that has not yet merged.
- **owner role**: `implementer` (authors); `verifier` (validator
  surfaces); `source` (ratifier of named exceptions).
- **current status**: Open; mitigation active. Scan checks run under
  every B2 validation pass.

### c.7 R-007 — Privileged mutation classes implemented without ratification

- **id**: `R-007`
- **description**: A privileged mutation (touching `deploy`,
  `governance`, `identity`, `security`, `attestation`, or
  `redaction`) is implemented under a non-privileged-looking
  envelope, or under an envelope that was never explicitly
  Source-ratified, because the envelope's `allowed_mutation_classes`
  did not name the privileged class. The privileged-class gate is
  side-stepped by mis-classification rather than by an explicit
  shortcut.
- **likelihood**: `Medium`. Mutation classes are not always obvious;
  an apparently-`docs` change to a governance document, for
  example, is in fact a privileged `governance` mutation.
- **impact**: `Severe`. Violates Feature 001 FR-006 / FR-008 and
  Feature 002 FR-008; corrupts the substrate.
- **mitigation**:
  1. [`../governance/MUTATION_CLASS_MODEL.md`](../governance/MUTATION_CLASS_MODEL.md)
     §a and §d are the authoritative class definitions; canonical
     governance / security / deploy documents and `.github/`
     content are explicitly `governance` / `security` /
     `deploy`-class even when the diff appears to be docs-only.
  2. [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b.6
     and §c require the dominant mutation class to be declared at
     readiness; the most privileged class drives the gate.
  3. The B2 envelope's `prohibited_surfaces` list (`.github/`,
     `.specify/`, `specs/`, `schemas/`, `validators/`, `templates/`,
     `examples/`, `tenants/`, `docs/product/`,
     `docs/architecture/`, `docs/governance/`, `docs/quality/`,
     `docs/devops/`, `docs/security/`, `docs/contracts/`,
     repository settings) keeps the B2 batch firmly inside the
     `docs` class.
  4. The validator's `mutation_class` check (Feature 001 FR-027a)
     surfaces class / action mismatches; the post-merge scope-audit
     field ([`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md)
     §b.5) requires explicit naming of any unexpected path.
- **trigger / early warning**: A diff under a `docs` envelope
  includes paths under `.github/`, `tenants/`,
  `docs/governance/`, `docs/security/`, or any other privileged
  surface. A spec wrapper sidecar's `allowed_mutation_classes`
  excludes a class whose paths are present in the diff.
- **owner role**: `architect` (envelope authoring); `source`
  (ratifier when re-classification is required); `verifier`
  (validator).
- **current status**: Open; mitigation active across DoR, DoD,
  governance docs, and the next-task protocol.

### c.8 R-008 — Branch / PR cleanup deleting branches without approval

- **id**: `R-008`
- **description**: A feature branch is deleted on the canonical
  remote (or a force-push rewrites canonical-branch history) under
  an envelope that did not authorize the cleanup. The destructive
  action is rationalized as housekeeping.
- **likelihood**: `Low`. Most envelopes explicitly prohibit
  destructive remote actions; the risk increases under post-merge
  "cleanup" framing.
- **impact**: `High`. Destroys audit evidence; may also break
  stacked branches that depend on the deleted branch.
- **mitigation**:
  1. [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.9
     requires cleanup state to be documented and any cleanup that
     mutates shared state to be ratified separately.
  2. [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.10
     requires the post-merge report to state whether the feature
     branch is to be deleted, retained, or requires Source approval
     before deletion. The default posture is retention pending
     explicit approval.
  3. The envelope's `prohibited_external_actions` list (Feature 002
     FR-005) names destructive remote actions (force-push, branch
     deletion) when those actions are not part of the batch.
- **trigger / early warning**: A post-merge report cites a deleted
  remote branch without a separate ratification record. A
  force-push appears in the canonical-branch reflog. A merge
  proposal cleans up a sibling branch as a side effect.
- **owner role**: `source` (ratifier of destructive cleanup);
  `implementer` (records cleanup state); `reviewer` (challenges
  unratified destructive actions).
- **current status**: Open; mitigation active. No destructive
  remote cleanup is authorized under B2.

### c.9 R-009 — Stacked-branch confusion while a predecessor branch is not yet on the canonical branch

- **id**: `R-009`
- **description**: A successor batch is authored on a feature branch
  stacked on top of a predecessor feature branch that has not yet
  landed on the canonical branch (the predecessor may already be
  delivery-view `Ratified` but its merge to canonical may still be
  sequenced under the post-merge protocol, or the predecessor's PR
  may still be open). Reviewers comparing the stacked branch against
  the canonical branch see the predecessor's changes mixed in with
  the successor's; or the predecessor branch is force-rebased and
  the stacked branch's parentage shifts silently.
- **likelihood**: `Medium`. Stacking is a routine technique whenever
  a successor batch begins before its predecessor has been
  canonicalized; the failure modes are quiet.
- **impact**: `High`. Misattributed scope audit; ambiguous
  ratification surface; cascading reverts on force-rebase.
- **mitigation**:
  1. The post-merge scope-audit field
     ([`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.5)
     names changed paths and explicitly reconciles the diff against
     the predecessor branch when one is named in the envelope's
     non-normative implementation context.
  2. [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.6
     requires PR / merge evidence to cite the merge commit SHA and
     the source / target branches, surfacing a stacked-branch
     parentage at merge time.
  3. [`./DEPENDENCIES.md`](./DEPENDENCIES.md) §c.1 names B1 → B2 as
     a `Ratified` or `Done` edge and records the current edge state;
     a successor envelope that advances while its predecessor edge
     is uncleared violates the dependency rule and surfaces in
     [`./BACKLOG.md`](./BACKLOG.md) review.
  4. Stacked-branch context is kept out of normative upstream
     content; only generic wording that survives after the
     predecessor lands on the canonical branch is included in the
     canonical artifacts.
- **trigger / early warning**: A scope-audit diff is computed
  against the canonical branch and includes the predecessor's
  changes; a reviewer cannot tell which commits belong to which
  batch; an upstream force-rebase changes the stacked branch's
  commit list without an envelope amendment.
- **owner role**: `implementer` (Hermes / Claude Code consumers
  managing stacking); `reviewer` (independent review of the
  successor batch); `source` (ratifier of any cross-branch
  resolution).
- **current status**: Open; mitigation active whenever a successor
  batch is authored against a predecessor that has not yet landed
  on the canonical branch.

### c.10 R-010 — Deferred US3 A1 being accidentally started

- **id**: `R-010`
- **description**: The reserved item `us3/a1` (per
  [`./BACKLOG.md`](./BACKLOG.md) §d and
  [`./DEPENDENCIES.md`](./DEPENDENCIES.md) §f) is interpreted as
  in-scope for an envelope because its id appears in upstream
  artifacts. An implementer treats the reservation as an invitation
  and begins work before Sprint 0 exits and before Source ratifies a
  future spec authorizing the area.
- **likelihood**: `Low`. The blocked / deferred posture is
  explicit; the risk increases under sustained pressure to "find
  the next thing to build."
- **impact**: `Severe`. Implementation is not authorized; starting
  work is an authority conflict per Feature 002 FR-018 and a
  violation of the Sprint 0 execution sequence in
  [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
  §5.
- **mitigation**:
  1. [`./BACKLOG.md`](./BACKLOG.md) §d records US3 A1 with
     `Blocked` / `Deferred` status and explicit absence of
     authorization.
  2. [`./DEPENDENCIES.md`](./DEPENDENCIES.md) §f names the two
     blockers (Sprint 0 exit AND Source-ratified future spec) and
     records that the mutation class is to be determined and MUST
     be treated as potentially privileged.
  3. Sprint 0 envelopes (Slice A, B1, B2) explicitly list "do not
     implement US3 A1" as a prohibition; any deviation triggers an
     immediate hard-stop per Feature 002 FR-018.
- **trigger / early warning**: A backlog row, an envelope, or a
  merge report names US3 A1 as the immediate next task without
  citing the two blockers as cleared. A consumer begins editing
  files that would only matter under a US3 A1 spec.
- **owner role**: `source` (authorization authority); `architect`
  (will scope a future spec if Source ratifies one); `implementer`
  (MUST hard-stop and escalate if asked to begin work).
- **current status**: Open; mitigation active. No implementation is
  authorized.

### c.11 R-011 — Controller-seat boundary breach

- **id**: `R-011`
- **description**: The controller (e.g., Nefarious / Hermes acting in
  a coordinating role) silently authors tracked files inside an
  implementer's envelope — typically a "small" Markdown link fix, a
  whitespace cleanup, or a docs reword — and the controller's edit
  is then verified by the controller themselves at the scope-audit
  stage. Author/approver separation per Feature 001 FR-007 collapses;
  the implementer-pane transcript no longer reflects the diff; the
  edit has no Source ratification of its own; and the
  controller-seat edit may mask a path-manifest-fidelity issue
  (R-012) the implementer would otherwise have surfaced.
- **likelihood**: `Medium`. The pressure to "save a round-trip" by
  editing from the controller seat is constant whenever the
  controller has filesystem access and the implementer pane is busy
  or paused.
- **impact**: `High`. Violates Feature 001 FR-007; corrupts the
  implementer-pane transcript as the system of record under
  [`../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md`](../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md);
  may produce diffs Source review cannot reproduce from artifacts.
- **mitigation**:
  1. [`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md)
     §d hardcodes the controller-verifies-never-authors rule and
     §e names the controller-seat-edit anti-pattern explicitly.
  2. [`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md)
     and [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md)
     name the controller / implementer boundary as a preflight check
     before any tracked-file mutation and before any mechanics.
  3. The Creator Engine validator's `role_boundary_attribution`
     check provides a verifier-side audit surface; when run with
     `--base <commit>`, it can be used to surface controller-seat
     attribution against a base commit.
  4. [`../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md`](../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md)
     §d closes the implementer-pane transcript with a recorded
     SHA256 so that any controller-authored content authored after
     the stop line is observable.
- **trigger / early warning**: A commit's diff includes paths the
  implementer-pane transcript does not show being authored; the
  controller's report-back claims to have "made a small fix" inside
  the implementer's manifest; a scope-audit run finds a path in the
  diff that the implementer never opened.
- **owner role**: `source` (boundary authority); `controller`
  (Nefarious / Hermes in coordinating seats); `implementer`
  (refuses to ratify content they did not author).
- **current status**: Open; mitigation active. Workflow-hardening
  protocol docs provide durable landed evidence: PR #22 /
  `d892cd3` (operations protocol docs, schemas, templates,
  validator checks) and PR #23 / `3dc45a1` (CI validator
  hardening, follow-up fixes).

### c.12 R-012 — Path-manifest / Markdown corruption (`__init__.py` regression class)

- **id**: `R-012`
- **description**: An envelope or handoff is relayed through a
  paste-pipeline path (chat pane, terminal multiplexer, clipboard)
  that corrupts Markdown around path manifests. The most-attested
  corruption strips double-underscores: the literal path
  `validators/creator_engine_validator/checks/__init__.py` arrives
  in the implementer's pane as
  `validators/creator_engine_validator/checks/init.py`. <!-- path_manifest_fidelity: pedagogical -->
  The implementer authors the corrupted path; the registry-running
  `__init__.py` is left untouched; the substrate diverges silently
  from the envelope. Adjacent regressions include duplicated paths,
  off-by-one counts, stripped blank lines, and reflowed code fences.
- **likelihood**: `Medium`. Paste corruption is the *default*
  outcome of relaying long Markdown bodies across surfaces that
  reinterpret formatting; it has been observed in prior batches.
- **impact**: `Severe`. The substrate diverges from the
  Source-ratified envelope without surfacing a single PR-level
  error; the controller's scope audit passes against the corrupted
  manifest; recovery requires Source ratification of an amended
  manifest and a fresh batch.
- **mitigation**:
  1. [`../operations/NO_COPY_PASTE_PATTERN.md`](../operations/NO_COPY_PASTE_PATTERN.md)
     codifies the pointer-only relay (path + expected SHA256 +
     consume-and-verify instruction). The manifest never travels
     through chat.
  2. [`../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`](../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md)
     names the fenced-block manifest shape, the normalized
     count/SHA256 computation, and the gates at which preflight
     runs (envelope publication, handoff consumption, tracked-file
     mutation, scope audit, mechanics).
  3. The Creator Engine validator's `path_manifest_fidelity` check
     emits the explicit `path_manifest_init_py_corruption` error
     class whenever a manifest line or a free-text reference inside
     the document body is the literal corrupted form
     `<package>/checks/init.py`, regardless of whether the declared
     count/hash also fail.
  4. [`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md)
     and [`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md)
     require the count/SHA256 to be declared and the implementer to
     recompute them before consumption.
- **trigger / early warning**: A handoff or envelope's authorized
  path manifest contains the literal token `checks/init.py` rather
  than `checks/__init__.py`; a declared `*_PATHS_COUNT` does not
  equal the unique-line count of the fenced block; a declared
  `*_PATHS_SHA256` does not equal the recomputed SHA256 of the
  normalized manifest.
- **owner role**: `source` (boundary authority); `architect` /
  `controller` (envelope and handoff authors); `implementer`
  (preflight recomputation); `verifier` (validator).
- **current status**: Open; mitigation active. Workflow-hardening
  protocol docs provide durable landed evidence: PR #22 /
  `d892cd3` (operations protocol docs, schemas, templates,
  validator checks including `path_manifest_fidelity` check) and
  PR #23 / `3dc45a1` (CI validator hardening, follow-up fixes).

### c.13 R-013 — Codex verification confused with Source ratification

- **id**: `R-013`
- **description**: A CFC-1 or future CFC batch Codex review verdict
  (`pass`, `pass_with_observations`) is treated as equivalent to
  Source ratification, and a privileged-class mutation is merged
  without explicit Source ratification. The verifies-not-ratifies
  invariant collapses in the Codex-specific context.
- **likelihood**: `Medium`. The risk is elevated for CFC follow-on
  batches where Codex review is explicitly informative and where the
  quality of Codex output may make it tempting to treat a positive
  verdict as sufficient.
- **impact**: `Severe`. Violates Feature 001 FR-008 and FR-013;
  corrupts the substrate audit trail; erodes the foundational
  principle that no AI review substitutes for Source ratification of
  any privileged class.
- **mitigation**:
  1. [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md)
     §3.5 explicitly prohibits Codex ratification authority for any
     artifact class.
  2. [`../operations/CODEX_FIRST_CLASS_PROTOCOL.md`](../operations/CODEX_FIRST_CLASS_PROTOCOL.md)
     §5 restates the verifies-not-ratifies invariant in the
     Codex-specific context with explicit verdict constraints.
  3. [`./REVIEW_GATE.md`](./REVIEW_GATE.md) names explicit criteria
     for when independent review evidence is required and how it is
     evaluated; a Codex verdict enters this gate as evidence, not as
     ratification.
  4. Feature 001 FR-013 and Feature 002 FR-013 are the authoritative
     substrate statements; any CFC envelope that purports to modify
     this invariant is a contract violation.
- **trigger / early warning**: A merge report cites a Codex verdict
  as governance evidence without a separate `repo_ratification_record`
  from Source. A PR description includes "Codex approved" as a
  substitute for Source ratification. A CFC batch envelope's ratifier
  field names Codex rather than `source`.
- **owner role**: `source` (sole ratifier); `controller` (Nefarious
  must not relay a Codex verdict as ratification); `implementer`
  (must not escalate a Codex verdict to ratification).
- **current status**: Open; mitigation active via scope doc §3.5 and
  protocol doc §5.

### c.14 R-014 — Codex actor authority or mutation-class scope creep

- **id**: `R-014`
- **description**: A CFC-1 or future CFC batch gradually expands the
  scope of Codex-authorized mutations — adding paths, mutation
  classes, or action types beyond the Source-ratified envelope —
  rationalized as "small" scope extensions needed for the batch.
  Each individual extension appears reasonable; together they expand
  Codex authority beyond the Source-ratified boundary.
- **likelihood**: `Medium`. Scope creep is common under time pressure;
  for CFC batches the risk is that the Codex-first-class framing is
  misread as implying Codex is already a fully authorized actor
  rather than an actor whose authority is bounded per envelope.
- **impact**: `Severe`. Violates Feature 001 FR-008; may introduce
  privileged mutations (identity, schema, governance) without Source
  ratification; corrupts the substrate.
- **mitigation**:
  1. [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md)
     §3 enumerates all non-authorized Batch 1 actions; any extension
     of the list requires a new Source-ratified envelope.
  2. The allowed path manifest in each CFC envelope is
     count-and-SHA256-verified; Codex must stop immediately if any
     path outside the manifest would be mutated.
  3. [`../operations/CODEX_FIRST_CLASS_PROTOCOL.md`](../operations/CODEX_FIRST_CLASS_PROTOCOL.md)
     §4 stop-line item 1 requires immediate escalation if a file
     outside the allowed manifest would be authored.
  4. The post-merge scope-audit field
     ([`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.5)
     surfaces unexpected paths.
- **trigger / early warning**: A CFC batch diff includes paths outside
  the Source-ratified allowed path manifest. A Codex session proposes
  creating an identity record, a schema, or an architecture document
  not in the manifest. A CFC envelope's `allowed_mutation_classes` is
  silently extended beyond the ratified class list.
- **owner role**: `source` (scope authority); `controller` (Nefarious
  catches manifest overflows); `implementer` (Codex must hard-stop at
  manifest boundary).
- **current status**: Open; mitigation active via scope doc §3 and
  protocol doc §4.

### c.15 R-015 — Codex author/approver collapse

- **id**: `R-015`
- **description**: The actor that authors a CFC batch artifact is also
  the actor that ratifies or independently reviews it, collapsing the
  author/approver separation required by Feature 001 FR-007. In the
  Codex-specific context this could arise if Codex authors artifacts
  and then its own review evidence is treated as independent
  verification, or if Nefarious authors the artifacts and then
  approves them as both controller and ratifier without Source being
  separate.
- **likelihood**: `Medium`. The CFC-1 framing explicitly names Codex
  as both a future author and a future reviewer, creating a surface
  for collapse if batch boundaries are not maintained.
- **impact**: `High`. Violates Feature 001 FR-007; corrupts the
  independent review gate; may allow self-certifying artifacts to
  merge.
- **mitigation**:
  1. [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md)
     §4.2 and §4.3 separately restate Nefarious's
     controller/reviewer/approver role and Claude Code's implementer
     role as distinct seats.
  2. [`../operations/CODEX_FIRST_CLASS_PROTOCOL.md`](../operations/CODEX_FIRST_CLASS_PROTOCOL.md)
     §3 defines evidence requirements; a Codex review of
     Codex-authored artifacts must be independently verifiable by
     Nefarious before Source ratification.
  3. Feature 001 FR-007 is the authoritative statement; any CFC
     envelope that assigns the same actor to author and ratify is a
     contract violation.
  4. Nefarious independently verifies Codex output before reporting
     to Source; Nefarious is the controller/reviewer, not the
     ratifier.
- **trigger / early warning**: A CFC batch shows the same actor
  (Codex or Claude Code or Nefarious) as both the artifact author and
  the ratifier. A review evidence record is authored by the same
  session that authored the artifacts under review. A merge report
  omits a distinct ratifier field.
- **owner role**: `source` (ratifier, by definition separate from any
  implementer); `controller` (Nefarious maintains the boundary);
  `architect` (envelope design must name distinct author and ratifier
  seats).
- **current status**: Open; mitigation active via scope doc §4.2 and
  §4.3 and protocol doc §3.

### c.16 R-016 — Controller-seat tracked-file authoring during CFC batches

- **id**: `R-016`
- **description**: During a CFC-1 or future CFC batch, Nefarious (in
  the controller/reviewer seat) directly authors tracked files that
  are in the implementer's (Claude Code's or Codex's) allowed path
  manifest — typically a "quick fix" to a newly-created governance or
  operations doc — without going through the implementer pane. This
  is a CFC-specific instance of R-011 with the additional
  complication that the CFC governance docs name Nefarious as the
  controller/reviewer, making it easier for the boundary to blur
  implicitly.
- **likelihood**: `Medium`. The CFC docs define Nefarious's role
  prominently; during batch execution the distinction between
  "Nefarious reading the draft" and "Nefarious authoring a paragraph"
  is easy to collapse under time pressure.
- **impact**: `High`. Violates Feature 001 FR-007; corrupts the
  implementer-pane transcript as the system of record; controller-
  seat edits to CFC governance docs specifically undermine the
  scope/protocol artifacts that are meant to define the boundary.
- **mitigation**:
  1. R-011 ([`./RISK_REGISTER.md`](./RISK_REGISTER.md) §c.11) is
     the general control; R-016 is the CFC-specific application.
  2. [`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md)
     §d hardcodes controller-verifies-never-authors; this applies
     during CFC batches without exception.
  3. [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md)
     §4.2 restates that Nefarious verifies and approves but does not
     author the Batch 1 tracked files.
  4. [`../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md`](../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md)
     §d closes the implementer-pane transcript; controller-authored
     content after the stop line is detectable.
- **trigger / early warning**: A CFC batch diff includes changes to
  CFC governance or operations docs that are not reflected in the
  implementer-pane transcript. Nefarious's report-back claims to have
  "made a small fix" to `CODEX_FIRST_CLASS_SCOPE.md` or
  `CODEX_FIRST_CLASS_PROTOCOL.md`. A scope-audit run finds a tracked
  path in the diff that the implementer never opened.
- **owner role**: `source` (boundary authority); `controller`
  (Nefarious must not edit tracked files in the implementer's
  manifest); `implementer` (refuses to ratify content they did not
  author).
- **current status**: Open; mitigation active via R-011 controls and
  scope doc §4.2.

### c.17 R-017 — Codex worktree isolation failure

- **id**: `R-017`
- **description**: During a future CFC batch where Codex acts as
  implementer, Codex shares a worktree with Claude Code or Nefarious,
  or writes directly to the canonical main branch without going
  through an isolated worktree and PR. The one-driver-per-worktree
  invariant is violated; concurrent writes from different sessions
  corrupt the worktree state; or Codex output is merged without a
  reviewable PR.
- **likelihood**: `Low`. The risk is low for Batch 1 (Claude Code is
  the Batch 1 implementer); it rises for any future CFC batch where
  Codex acts as the primary tracked-file author.
- **impact**: `High`. Violates
  [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
  §d.2 (one-driver-per-worktree); may produce merges without
  independent review; corrupts the audit trail.
- **mitigation**:
  1. [`../operations/CODEX_FIRST_CLASS_PROTOCOL.md`](../operations/CODEX_FIRST_CLASS_PROTOCOL.md)
     §2 defines Codex-only worktree isolation with a `-codex-review`
     suffix naming convention and explicit prohibition on writing to
     Claude Code worktrees or canonical main.
  2. [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
     §d.2 applies without exception; Codex worktrees follow the same
     one-driver rule.
  3. [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md)
     §4.4 restates Codex worktree isolation as a governance
     requirement; isolation does not substitute for Source
     authorization.
  4. Any Codex-authored batch must go through an isolated worktree →
     PR → Source ratification → merge path; no direct-to-main write
     is authorized.
- **trigger / early warning**: A Codex session is found to have
  authored files in a worktree that also has an active Claude Code
  session. A Codex-authored commit appears on canonical main without
  a corresponding PR. Two different actor sessions share the same
  worktree directory.
- **owner role**: `source` (authorizes Codex batches); `controller`
  (Nefarious must verify isolation before authorizing a Codex
  session); `implementer` (Codex must stop if isolation invariants
  cannot be satisfied).
- **current status**: Open; mitigation active via protocol doc §2.

### c.18 R-018 — Provider/tool/model/host/account binding leakage into upstream docs

- **id**: `R-018`
- **description**: A CFC-1 or future CFC batch binds a concrete
  provider, tool, model version, host installation, or account into
  the governance scope or operations protocol documents. The upstream
  tree picks up a dependency on a specific deployment decision that
  should remain a deployment-time overlay.
- **likelihood**: `Medium`. CFC batches are explicitly about making
  Codex first-class; the temptation to name specific tools, models,
  or API endpoints is high when drafting protocol docs that describe
  how Codex should act.
- **impact**: `High`. Violates Feature 002 FR-025
  (implementation-agnostic substrate); makes the governance docs
  non-portable; forces a Source-ratified amendment whenever the
  concrete binding changes.
- **mitigation**:
  1. [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md)
     §3.7 explicitly prohibits provider/tool/model/host/account
     binding in Batch 1.
  2. [`../operations/CODEX_FIRST_CLASS_PROTOCOL.md`](../operations/CODEX_FIRST_CLASS_PROTOCOL.md)
     is written in implementation-agnostic language; it names "Codex"
     as an actor-role label, not as a specific model-version or API
     product.
  3. The allowed path manifest for Batch 1 does not include any
     `tenants/`, `schemas/`, or deployment-overlay paths where
     bindings would normally live.
  4. The Creator Engine substrate's `scan-no-limitless` check may
     be extended to surface concrete model/provider strings in
     governance docs.
- **trigger / early warning**: A CFC batch diff includes a concrete
  model, provider, API endpoint, account, or host binding in a
  governance or operations doc. A protocol doc names a specific API
  endpoint URL. A governance doc names a specific account or host
  path.
- **owner role**: `source` (binding authority); `architect` (ensures
  protocol docs remain binding-agnostic); `implementer` (stops if a
  concrete binding appears in a draft).
- **current status**: Open; mitigation active via scope doc §3.7 and
  implementation-agnostic doc authoring.

### c.19 R-019 — Batch 1 accidentally absorbing Batch 2 or Feature 005 scope

- **id**: `R-019`
- **description**: CFC-1 Batch 1 grows to include identity record
  creation, review-evidence schema authoring, architecture actor/tool
  matrix updates, or Feature 005 dispatch automation — any of the
  explicitly deferred items in
  [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md)
  §3. The batch expands silently because each addition appears to be
  a "natural next step" from the scope/protocol substrate work.
- **likelihood**: `Medium`. The CFC-1 framing makes it easy to reason
  that "while we're documenting Codex scope, we should also create
  the identity record" or "while we're writing the protocol, we
  should also add the schema." Each individual addition is locally
  motivated; together they absorb Batch 2+ scope.
- **impact**: `Severe`. Any absorbed Batch 2 item is a
  privileged-class mutation that was not Source-ratified under the
  Batch 1 envelope; this is a contract violation per Feature 001
  FR-008 and Feature 002 FR-018.
- **mitigation**:
  1. [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md)
     §3 enumerates all non-authorized Batch 1 items; each item
     requires a separate Source-ratified envelope.
  2. The allowed path manifest for Batch 1 (7 paths; count and SHA256
     verified) explicitly excludes all `tenants/`, `schemas/`,
     `docs/architecture/`, and any other Batch 2+ path.
  3. [`../operations/CODEX_FIRST_CLASS_PROTOCOL.md`](../operations/CODEX_FIRST_CLASS_PROTOCOL.md)
     §4 stop-line item 5 requires Codex to stop immediately if
     instructions appear to expand scope to any §3-prohibited item.
  4. [`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md)
     §5 records the deferred items with their expected class and gate,
     making it explicit that each requires a separate envelope.
- **trigger / early warning**: A Batch 1 diff includes a file under
  `tenants/`, `schemas/`, `docs/architecture/`, or any other
  Batch 2+ path. A draft of a CFC artifact includes language that
  reads like an identity record section. An envelope proposes to
  "also" add the review-evidence schema. A Feature 005 dispatch
  automation concept appears in a protocol draft.
- **owner role**: `source` (scope authority); `controller` (Nefarious
  must catch scope leakage before reporting to Source); `implementer`
  (must hard-stop and escalate if a scope expansion is implicated).
- **current status**: Open; mitigation active via scope doc §3 and
  path manifest verification.

## d. Maintenance rules

1. Risks are added or amended in this document; the addition is
   recorded in the post-merge documentation-impact field per
   [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.6.
2. A risk is closed only when its mitigation has rendered the
   trigger unreachable under the current contracts; closure is
   itself a `governance`-class amendment and requires Source
   ratification per Feature 001 FR-008.
3. The "owner role" field names a Feature 001 baseline role
   category, not a specific operator. Tenant-specific overlays MAY
   resolve the role to a named operator in
   `tenants/<name>/authority-matrix-overlay.yml`; the substrate
   register MUST NOT.
4. Instance-local facts (absolute filesystem paths, in-flight PR
   numbers, terminal pane identifiers, local session queues,
   secrets, credentials, tokens) MUST NOT enter this document.
   Merged PR numbers in canonical-branch commit subjects MAY be
   cited as historical evidence.

## e. Acceptance posture for B2

This document satisfies the B2 envelope's risk-register
requirements:

- Includes the ten named risks (§c.1–§c.10): scope creep into
  building a Jira clone (R-001); external tracker canonicalization
  / SaaS dependency (R-002); skipping Source ratification because
  CI or an agent review passes (R-003); stale backlog or Kanban
  after a merge (R-004); status vocabulary confusion between
  delivery-view statuses and Feature 001 lifecycle statuses
  (R-005); instance-local facts leaking into upstream docs (R-006);
  privileged mutation classes implemented without ratification
  (R-007); branch / PR cleanup deleting branches without approval
  (R-008); stacked-branch confusion while an upstream PR remains
  unmerged (R-009); and deferred US3 A1 being accidentally started
  (R-010).
- Each risk row includes id, description, likelihood, impact,
  mitigation, trigger / early warning, owner role, and current
  status.

The register is extended by the workflow-hardening protocol set
([`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md),
[`../operations/NO_COPY_PASTE_PATTERN.md`](../operations/NO_COPY_PASTE_PATTERN.md),
[`../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`](../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md),
and [`../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md`](../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md)),
which has landed on the canonical branch as durable evidence under
PR #22 / `d892cd3` and PR #23 / `3dc45a1`, to include:

- R-011 (controller-seat boundary breach) in §c.11.
- R-012 (path-manifest / Markdown corruption, the `__init__.py`
  regression class) in §c.12.

Both rows follow the existing row style. The B2 acceptance posture
above remains intact for the original ten risks.

The register is further extended by the CFC-1 Batch 1 governance
scope and operations protocol substrate work to include:

- R-013 (Codex verification confused with Source ratification) in
  §c.13.
- R-014 (Codex actor authority or mutation-class scope creep) in
  §c.14.
- R-015 (Codex author/approver collapse) in §c.15.
- R-016 (controller-seat tracked-file authoring during CFC batches)
  in §c.16.
- R-017 (Codex worktree isolation failure) in §c.17.
- R-018 (provider/tool/model/host/account binding leakage into
  upstream docs) in §c.18.
- R-019 (Batch 1 accidentally absorbing Batch 2 or Feature 005
  scope) in §c.19.

All seven rows follow the existing row style. Upstream sources for
the CFC-1 risks are
[`../governance/CODEX_FIRST_CLASS_SCOPE.md`](../governance/CODEX_FIRST_CLASS_SCOPE.md)
and
[`../operations/CODEX_FIRST_CLASS_PROTOCOL.md`](../operations/CODEX_FIRST_CLASS_PROTOCOL.md).
The B2 and workflow-hardening acceptance postures above remain intact.
