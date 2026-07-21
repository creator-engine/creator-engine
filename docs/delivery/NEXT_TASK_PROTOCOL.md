# Post-Merge Next-Task Protocol

**Status**: Sprint 0 Slice B1 scaffold, cross-referenced from Slice B2
(Definition of Ready, Definition of Done, dependency map, risk
register). Part of the **minimum repo-native delivery control plane**
and **not a Jira clone**. A fresh clone is sufficient to apply this
protocol; no external tracker credential or network state is required.

The ten report fields in §b and the selection rules in §c are
unchanged by Slice B2. Slice B2 supplies the readiness and completion
gates the report fields are evaluated against
([`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) and
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md)), the dependency
map the next-task selection rules walk
(`./DEPENDENCIES.md`), and the standing risks
that bear on report authoring
(`./RISK_REGISTER.md`). Where this protocol and
the Slice B2 documents reference the same field, the protocol
controls for procedure; the Slice B2 documents control for the gate
the procedure evaluates against.

## a. Purpose

After every merge to the canonical branch, a completion report MUST be
produced. The report's job is to make the next governed Creator
Engine task identifiable from repository content alone — without
relying on chat memory, transient runtime context, or external tracker
state.

This document specifies (i) the ten required completion-report fields,
(ii) the procedure for refreshing
`./BACKLOG.md` and
`./KANBAN.md`, and (iii) the rules by which the next
task is selected.

The ten fields below are the same ten fields named in
[`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
§7. A merge report that does not include them is incomplete.

## b. Required completion-report fields

Every merge completion report MUST include each of the ten fields
below, in order. The example phrasings are illustrative; the binding
requirement is that the field is named, populated, and reconstructable
from repository artifacts.

### b.1 Merge identification

Identify the merge unambiguously. State the PR number (when present),
the source branch, the target (canonical) branch, the merge commit
SHA, and the feature / slice id that the merge advances. Example:
"merge commit `<sha>` from branch `<branch>` into `main`; advances
`sprint-0/slice-b/b1`."

### b.2 Scope summary

Summarize what changed and what intentionally did not change. List
the changed paths or path groups. Name any surfaces that were
explicitly out of scope per the batch envelope (e.g., "no `.github/`,
`specs/`, or `tenants/` mutations").

### b.3 Validation evidence

Name the pushed current-head SHA and required Validate run URL/status
for that exact head (or required synthetic merge-group head), plus any
optional targeted author checks. Local full-suite transcripts are not
accepted as gate evidence; independent review and ratification are
recorded under §b.4.

### b.4 Governance evidence

Name the mutation classes touched, the ratification record(s)
applicable, and the review / attestation evidence. For non-privileged
classes, cite the review evidence. For privileged classes (`deploy`,
`governance`, `identity`, `security`, `attestation`, `redaction`),
cite the Source ratification record per Feature 001 FR-008 and
FR-016.

### b.5 Scope audit

Confirm that no prohibited surface was mutated. Cite the surfaces the
envelope declared `prohibited_surfaces` (or equivalent). Name any
unexpected paths that appeared in the diff and the resolution
(reverted; or reclassified under a ratified envelope amendment).

### b.6 Documentation impact

Name any canonical document, source-of-truth artifact, or contract
that was changed or that requires a follow-up edit. If
`docs/delivery/` artifacts (`README.md`, `BACKLOG.md`, `KANBAN.md`,
`NEXT_TASK_PROTOCOL.md`, or later B2 documents) were changed, name
them; if none changed, state "none."

### b.7 Deferred work

Enumerate work explicitly deferred by this merge, with the owning
future slice or feature. Deferred items MUST appear in
`./BACKLOG.md` with status `Deferred` or `Blocked`
and a named dependency / blocker.

### b.8 Readiness impact

Name the Sprint 0 exit gate(s) that advanced and the gate(s) that
remain blocked. Cite the gate numbers from
[`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
§4. If a gate is partially advanced (e.g., gate #2 advanced by B1 but
not satisfied until B2 lands), say so explicitly.

### b.9 Immediate next-task recommendation

Recommend exactly one next governed task and the rationale for the
choice. Selection rules live in §c. If the rules surface no
unambiguous next task, the recommendation MUST be either (i) a
backlog refresh + escalation to Source, or (ii) the named blocker as
the implied next task. Do not improvise.

### b.10 Cleanup state

Describe the cleanup state of the development environment: branch
state on the canonical remote; worktree state; whether the feature
branch is to be deleted, retained, or requires Source approval before
deletion; whether any local snapshot file (e.g.,
`.ce/state/session-state/STATE.md` in deployed instances) needs an
update. Cleanup actions that mutate shared state (deleting remote
branches, force-pushes) MUST be ratified separately.

## c. Next-task selection rules

The next-task recommendation in §b.9 MUST be derived by applying these
rules in order. Stop at the first rule that yields a recommendation.

### c.1 Highest-priority `Ready` item

Select the highest-priority backlog item whose status is `Ready` and
whose dependencies are satisfied (every named dependency is at
`Ratified` or `Done`). Priority is given by parent-slice ordering in
`./BACKLOG.md`: Sprint 0 slices precede post-Sprint-0
features; within Sprint 0, slices are sequenced A → B → C → D → E →
F; sub-batches are sequenced numerically (e.g., B1 → B2 → B3 → B4).

### c.2 Highest-priority `Backlog` item with a clear readiness path

If no `Ready` item qualifies under §c.1, select the highest-priority
`Backlog` item whose readiness path is clear (its dependencies are
identifiable, its scope is shapeable, and its owning future slice or
feature is named). The recommendation MUST include the shaping step
required to promote the item to `Ready`.

### c.3 Ambiguous or stale backlog

If the backlog is ambiguous (multiple items tie under §c.1 / §c.2 and
no parent-ordering rule resolves the tie) or stale (rows reference
artifacts that no longer exist, or rows lack an upstream source of
truth), the recommendation MUST be a backlog refresh and an
escalation to Source. The escalation names the ambiguity / staleness
and asks Source to ratify the corrected state before any new
Assignment Envelope is authored.

### c.4 Blocked item

If every candidate is `Blocked`, the named blocking dependency is the
implied next task. The recommendation MUST cite the blocked item, the
blocker, and the action required to clear the blocker (e.g., "advance
`sprint-0/slice-b/b2` to `Done` to unblock `sprint-0/slice-c`").

### c.5 Privileged blocker — ratification request

If the action required to clear the blocker is itself a privileged
mutation (a change touching `deploy`, `governance`, `identity`,
`security`, `attestation`, or `redaction`), the next task is a
ratification request to Source, **not** the implementation. The
implementation does not begin until ratification is recorded per
Feature 001 FR-016 / FR-020a.

### c.6 External-tracker disagreement

If an external tracker entry disagrees with the repo-visible backlog
about status, scope, dependencies, or readiness, the repo-visible
backlog controls until Source ratifies an update. The recommendation
MUST cite the repo-visible state, note the disagreement, and (if
relevant) name the tracker-mirror reconciliation work as a future
non-canonical adapter concern per [`./README.md`](./README.md) §d. An
external tracker entry MUST NOT, by itself, justify a change to the
repo-visible backlog.

## d. Post-merge update procedure

After applying §b and §c, perform the following before closing the
report:

1. Update `./BACKLOG.md` so that every item's status,
   dependencies, and evidence reference reflect the merged state.
2. Update `./KANBAN.md` so that every column reflects
   the new backlog state. The Kanban view is a derivative; it does
   not introduce new ids.
3. Confirm that the canonical documents in `docs/product/`,
   `docs/architecture/`, `docs/governance/`, `docs/quality/`,
   `docs/devops/`, `docs/security/`, and `docs/contracts/` were not
   silently amended by the merge unless the envelope authorized it.
   Any canonical-doc change requires Source ratification per Feature
   001 FR-008 (`governance` class is privileged).
4. Confirm that the Feature 001 spec-status lifecycle values on the
   affected spec(s) match the delivery-view statuses applied here.
   The delivery view MUST NOT amend the canonical lifecycle.
5. Confirm that no instance-local facts entered the upstream tree.
   See §e.
6. **Path-manifest hash verification.** If the merge advanced a
   batch authored under a fenced path manifest per
   [`../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`](../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md)
   §c, the report-author confirms that the merge commit's
   changed-file set, when normalized (sorted, deduplicated, LF-joined
   with one trailing newline, UTF-8) and SHA256-hashed, equals the
   envelope's declared `*_PATHS_SHA256` value. The
   `path_manifest_fidelity` validator's recomputation provides this
   value mechanically; the report cites both hashes if they
   disagree. The hash also serves as the input to the next batch's
   handoff per [`../operations/NO_COPY_PASTE_PATTERN.md`](../operations/NO_COPY_PASTE_PATTERN.md)
   when a successor envelope re-uses or extends the manifest.
7. **Root-worktree invariant check.** At session start (before any
   new envelope is consumed and before §c selection rules are
   applied) and again after every merge-close gate (before §b.10
   cleanup state is finalized), the report-author confirms the four
   conditions of the root-worktree invariant against the root
   checkout per
   [`../operations/ROOT_WORKTREE_INVARIANT.md`](../operations/ROOT_WORKTREE_INVARIANT.md)
   §c: the root is on the canonical branch; the root's HEAD is equal
   to live `origin/main` after a `git fetch origin main`; the root's
   working tree has no staged paths, no unstaged tracked
   modifications, and no untracked top-level scratch that is not
   ignored; and the root carries no in-flight substantive authoring.
   These checks are read-only against the root and MUST NOT mutate
   the root in the act of checking. A failure on any condition is a
   halt-to-shape signal per
   [`../operations/ROOT_WORKTREE_INVARIANT.md`](../operations/ROOT_WORKTREE_INVARIANT.md)
   §e: the report-author MUST NOT opportunistically clean the root,
   MUST NOT silently stage/commit/push, MUST surface the dirty-root
   observation in the §b.10 cleanup-state field, and MUST route the
   remediation to a separately Source-ratified envelope. The §b.9
   next-task recommendation under a dirty root SHOULD be the
   remediation envelope shaping (or the §c.3 escalation to Source)
   rather than the consumption of a new substantive authoring
   envelope.

## e. Prohibited content in this protocol and in the artifacts it updates

The following MUST NOT appear in `BACKLOG.md`, `KANBAN.md`,
`NEXT_TASK_PROTOCOL.md`, this protocol document, or any later
`docs/delivery/` artifact created under this protocol:

- Absolute filesystem paths of any specific operator's clone.
- Live branch names tied to in-flight instance batches, used as
  normative upstream state.
- Live PR numbers or PR URLs of open work-in-progress (merged PR
  numbers from canonical-branch commit subjects MAY be cited as
  historical evidence).
- Terminal multiplexer pane identifiers, session names, or other
  runtime identifiers from any specific operator's environment.
- Local session queues, carry-forward queues, or other instance-local
  runtime state. Those belong in an instance-local ignored file per
  [`../operations/session-continuity-protocol.md`](../operations/session-continuity-protocol.md).
- Secrets, credentials, tokens, account identifiers, or environment
  variables holding such values.
- Real tenant or customer identifiers beyond the generic references
  already ratified in the substrate.

Promoting any such fact into an upstream artifact is itself a
governance violation and MUST be reverted unless Source ratifies a
named exception.

## f. Acceptance posture for B1 (extended by B2)

This document satisfies the B1 envelope's protocol requirements and
is cross-referenced from the Slice B2 documents
([`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md),
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md),
`./DEPENDENCIES.md`,
`./RISK_REGISTER.md`) without altering the ten
report fields:

- All ten post-merge fields from
  [`../../specs/sprint-0-minimum-viable-delivery-system/README.md`](../../specs/sprint-0-minimum-viable-delivery-system/README.md)
  §7 are named and described: Merge identification, Scope summary,
  Validation evidence, Governance evidence, Scope audit,
  Documentation impact, Deferred work, Readiness impact, Immediate
  next-task recommendation, and Cleanup state.
- Next-task selection rules cover the six required cases: highest-
  priority `Ready` item; highest-priority `Backlog` item with a
  clear readiness path; ambiguous / stale backlog escalation;
  blocked item routes to the named blocker; privileged blocker
  routes to a ratification request rather than to implementation;
  external-tracker disagreement routes to the repo-visible backlog
  until Source ratifies an update.
- The delivery-view status vocabulary (`Backlog`, `Ready`,
  `In Progress`, `Verified`, `Ratified`, `Done`, `Deferred`,
  `Blocked`) is consistent with
  `./BACKLOG.md` §a and
  `./KANBAN.md` §a, and is explicitly delivery-view
  only — it does not amend the Feature 001 spec-status lifecycle.
- Instance-local facts are explicitly prohibited from upstream
  delivery artifacts.

## f. Non-merge ratified gates (cross-reference to Completion Report Substrate)

The ten fields in §b are the canonical post-merge report. For
ratified gates that do **not** end at a canonical-branch merge —
PR-only edits, non-Git runtime / config / provider mutations,
read-only research, and blocked / aborted gates — the substantive
return packet is a Completion Report artifact authored against
`schemas/completion-report.schema.yaml`. The prose contract,
trigger taxonomy, per-class required fields, and canonical absence
reasons live at
[`../operations/COMPLETION_REPORT_PROTOCOL.md`](../operations/COMPLETION_REPORT_PROTOCOL.md).

This protocol does NOT duplicate the ten merge fields in the
completion-report schema; the schema's class-C-merge `merge_report`
object encodes the same facts in machine-readable form, and §b
above continues to control for human review of a merge gate. The
two surfaces are complementary, not redundant.

For class C-merge, authors satisfy this protocol's §b and the
class-C-merge schema fields together. For all other ratified-gate
classes (A, C-pr-only, D, E, F), the completion-report artifact is
the return packet; §b does not apply.
