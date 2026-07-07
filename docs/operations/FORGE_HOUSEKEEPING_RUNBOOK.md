# Forge Housekeeping Runbook

Status: operational runbook for takeover and standby controllers.

This runbook codifies the forge housekeeping loop that a controller must run
after workers signal completion. It is written for a hydrated standby or
takeover controller that has no access to predecessor session memory.

## Scope

Use this runbook for controller-owned forge work after an implementer, reviewer,
verification lane, or automation lane reports a branch, PR, verdict, or merge
candidate. It covers harvest, independent review routing, gate preparation,
post-merge closeout, re-push handling, and board hygiene.

This runbook does not grant authority. It describes required evidence and
operator-facing decisions. Authority still comes from the active controller
posture, governed launch evidence, reviewer venue evidence, approval-wall rules,
and any explicit Operator direction in force for the repository.

## Controller Forge Loop

1. Signal intake.

   Record the worker or lane signal exactly as received: branch, base, head SHA,
   worktree path, stop line, validation evidence, changed paths, ticket, and PR
   URL if one already exists. Treat the signal as a claim that must be harvested,
   not as gate evidence by itself.

2. Harvest.

   Check out or inspect the signaled head without mutating unrelated work. Verify
   that the branch is based on the intended base and that the committed head is
   the one named in the signal. Run the full local preflight required for the
   current repo policy before any commit-for-harvest, self-push, or gate handoff:
   `ce validate-pr` with CI parity unless the governing brief names a stricter
   command.

   Confirm carrier fidelity before routing review:

   - The PR carrier slug matches the branch slug.
   - The carrier path set equals the actual `base..HEAD` diff and includes the
     carrier itself.
   - The changelog fragment exists when the path-manifest gate requires it.
   - The declared work class is honest for the diff and is not below the local
     work-sizing floor.

3. Independent review venue.

   Route substantive review to an independent venue where author != reviewer.
   A controller must not treat an author's self-check, inline notes, or prior
   approval on an older head as the required independent review.

   Review verdicts bind to the current head SHA. Evidence must name the head,
   reviewer identity, commands or reproductions run, changed paths considered,
   and verdict. Store durable review evidence in the expected evidence file or
   PR comment location before using it for gate decisions. If a verdict is
   posted without head binding, request a corrected current-head verdict instead
   of inferring intent.

4. Gate act.

   The gate act is separate from review. Approval is the merge trigger only when
   the controller posture and repo policy say that this controller may exercise
   that gate authority, all current-head evidence is fresh, required checks are
   green, carriers are faithful, and no board blocker remains.

   Capability markers are fresh-head artifacts. If the head changes, the marker
   is stale until regenerated or revalidated by the approved mechanism. Never
   carry a stale marker, stale approval, or stale verdict across a force-push.

5. Post-merge closeout.

   After merge is observed, close the loop in this order:

   - Confirm the merged commit or squash result reached the intended base.
   - Transition work claims from active to complete, or record supersession if
     the merge obsoletes another claim.
   - Collate changelog fragments according to the release or project process.
   - Re-check the board for dependent PRs, stale review state, blocked tickets,
     and awaiting-operator items that can now advance.
   - Leave a concise durable note with PR, merged head, validation evidence, and
     any follow-on queue changes.

## Re-Push Mechanics

Verdicts, approvals, and capability markers bind to a specific PR head. A new
push creates a new review object even if the visible branch name is unchanged.

On any re-push:

1. Compare the old approved head to the new head.
2. Regenerate the path-manifest carrier when the path set changes.
3. Re-run full local preflight before the next push or harvest commit.
4. Request delta re-review for changed code, docs, generated artifacts, carrier
   changes, and any changed evidence file.
5. Treat force-pushes as approval invalidation unless a machine restamp policy
   proves base-only equivalence and the repo's policy permits that restamp.

Carrier regeneration is mandatory when any file enters or leaves the diff. A
path-set mismatch is a gate blocker even when the substantive code looks right.

Ledger-touching PRs must be serialized. Brain assertions and similar append-only
ledgers form a global chain: concurrent PRs that each append to the same chain
can be individually valid while pairwise conflicting after one lands. Land one
ledger PR, update the next branch from the new base, regenerate affected
carriers, and re-run preflight before reviewing the next head.

## Takeover Hydration Use

`ce takeover` hydration must surface this runbook as an artifact pointer during
the Hydrate phase. A standby controller should read it together with takeover
evidence, brain bootstrap state, active-work ledger state, queue state,
approval-wall state, and watcher manifests before running a harvest-to-closeout
cycle.

The runbook is additive. It composes with the takeover hydration contract by
making the forge-housekeeping procedure discoverable; it does not replace the
machine-readable hydration read list or add new write authority.

## Proposal: operator-decision-pending

Open question: how should a legitimate takeover controller reconcile the
repository-level `AGENTS.md` hard-stop rule that says never approve or merge
with controller-gate handoff language that may require a takeover controller to
exercise gate acts?

Proposed resolution, pending Operator decision:

- `AGENTS.md` remains binding for ordinary workers, reviewers, and uncontrolled
  controller launches.
- A takeover controller may perform gate acts only when launched under governed
  takeover evidence, the drill harness proves the posture, and an explicit
  Operator decision or ratified controller-gate policy grants that authority.
- Without that explicit grant, the takeover controller stops at
  awaiting-operator with complete evidence, recommended action, and no approval,
  merge, enqueue, or signing side effect.

Until the Operator ratifies a resolution, controllers must treat this section as
proposal text only. Do not edit `AGENTS.md` as part of this runbook.

## Board Hygiene Cadence

Run board hygiene at controller start, after every PR push observed, after every
review verdict observed, after every merge, and before ending a controller
session.

Cadence checklist:

- Watchers: confirm queue, conveyor, review, claim, and approval-wall watchers
  are present or intentionally absent. Re-arm only through dry-run-visible,
  governed commands from the duty manifest.
- Stale approvals: find approvals, verdicts, and capability markers whose head
  SHA differs from the live PR head. Mark them stale and request current-head
  review before gate action.
- Awaiting-operator queue: surface unresolved decisions, posture conflicts,
  break-glass requests, policy waivers, and blocked gate acts in one explicit
  operator-facing queue.
- Claims: release completed claims, flag stale claims for explicit takeover
  rather than silent reuse, and preserve structured release/takeover history.
- Dependencies: re-check dependent tickets and PRs after each merge so ready work
  can advance without waiting for predecessor session memory.

## Drill Acceptance

A standby controller hydrated only from repository artifacts should be able to
execute this sequence in a drill:

1. Read takeover evidence and this runbook.
2. Harvest one completed branch and verify full preflight, carrier fidelity, and
   honest work class.
3. Route independent current-head review and persist evidence.
4. Stop at the correct gate posture: either perform a permitted gate act with
   fresh evidence or surface an awaiting-operator item when authority is absent.
5. After an observed merge, transition claims, collate changelog material, and
   re-check the board.
