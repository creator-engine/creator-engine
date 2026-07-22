# Workflow-As-Artifact Catalog

Status: prose contract. This document defines the named reusable governed
workflows that may be published as workflow artifacts. It is a catalog of
reviewable templates, not a runtime implementation and not a live authorization
grant.

## Contract

A cataloged workflow is a governed artifact with a stable name, purpose, input
contract, ordered steps, authority classification, and idempotency rules. Active
use of a workflow still requires the normal governance path for the surrounding
work: scoped inputs, path and authority bounds, independent evidence where
required, and ratification for reserved action classes.

Catalog entries use the autonomous and reserved action vocabulary ratified by
the orchestrator action taxonomy in
`ADR-0013-substrate-independent-authority`. Forge events that start or resume a
workflow should map to the trigger taxonomy in
`COMPLETION_REPORT_PROTOCOL`, including issue, pull request, CI, schedule,
webhook, mention or command, delay, and dedup windows. A trigger may enqueue,
resume, or propose work; it does not authorize mutation by itself.

Future slices may formalize these entries as `workflow.json` plus sibling step
prompt files. This document intentionally defers JSON schema formalization and
runtime registration.

## Artifact Shape

Each workflow artifact should carry these fields when it is formalized:

| Field | Meaning |
| --- | --- |
| `name` | Stable kebab-case workflow name. |
| `purpose` | One-sentence outcome and boundary. |
| `inputs` | Required evidence, refs, envelopes, claims, and scope constraints. |
| `governed_steps` | Ordered actions with explicit stop conditions. |
| `classification` | Autonomous, reserved, or mixed, using the ADR-0013 taxonomy. |
| `idempotency` | Deterministic keys, dedup windows, and safe re-run behavior. |

## Catalog

### `review-gate`

Purpose: route an authored change through independent review evidence and merge
eligibility checks without letting the author ratify the work.

Inputs:

- Pull request ref, base ref, declared work class, and carrier path set.
- CI status, required-check names, and merge-queue or branch-protection state.
- Reviewer identity evidence showing author and reviewer separation.
- Review evidence packet or explicit changes-requested verdict.

Governed steps:

1. Confirm the PR has a closed path set and exactly one declared work class.
2. Confirm the required Validate run URL/status is green and bound to the
   current pushed head (or required synthetic merge-group head), or identify the
   failing gate. Local full-suite transcripts are not gate evidence.
3. Route review to an independent reviewer or harvest an existing independent
   verdict.
4. Reconcile stale review, base drift, and unresolved review threads.
5. Gate merge eligibility only after review, CI, declared class, and scope
   predicates all hold.

Classification: mixed. Review routing, check watching, stale-review detection,
and return-to-author are autonomous when predicates hold. Merge, policy
exception, guard weakening, release, deploy, and any missing-predicate override
remain reserved.

Idempotency and dedup: key by repository, PR number, head SHA, base SHA, and
review verdict SHA. Re-running may update evidence and return status, but must
not duplicate reviewer requests inside the active dedup window or submit a
second verdict for the same reviewer/head pair.

### `harvest-preflight-pr`

Purpose: turn worker output into a governed delivery PR while preserving scope,
evidence, and carrier discipline.

Inputs:

- Worker brief pointer and hash, role, scope, stop lines, and allowed paths.
- Worker output summary, changed path list, validation evidence, and residual
  risks.
- Target branch name, base ref, issue or work item pointer, and declared work
  class.

Governed steps:

1. Compare worker output against the brief, stop lines, and allowed path set.
2. Refuse or return to author if changed paths exceed the dispatched envelope.
3. Generate changelog and path-manifest carriers from the committed diff and
   commit the complete final path set.
4. Push that final committed head and open or update the delivery PR with work
   class and residual-risk notes.
5. Wait for the required Validate result bound to that exact head, then attach
   the run URL/status as evidence. Targeted author tests remain optional
   iteration evidence only.

Classification: autonomous for ordinary in-scope delivery PR creation and
updates. Reserved if the output requests broader paths, broader credentials,
live settings, deploy, release, history rewrite, or a governance exception.

Idempotency and dedup: key by branch, base ref, diff path-set hash, and worker
brief hash. Re-running regenerates carriers from the current diff and updates
the existing PR rather than opening a duplicate PR for the same branch.

### `dispatch-watch-harvest`

Purpose: dispatch a role-shaped worker, monitor the run, and harvest only the
authorized output.

Inputs:

- Work item, dependency state, active claim, and collision-check result.
- Role definition, least-authority tool envelope, allowed paths, and stop
  conditions.
- Worker brief pointer and hash, expected artifacts, and validation command.

Governed steps:

1. Confirm dependencies are satisfied and no active conflicting claim wins.
2. Dispatch the worker with a self-contained brief and least-authority role.
3. Watch for completion, blocked state, scope drift, or missing evidence.
4. Harvest output only if paths, artifacts, and evidence match the brief.
5. Release or update the claim with the final status and next action.

Classification: autonomous when the dispatch is file-disjoint, role-scoped,
and within the active run mode. Reserved if dispatch would broaden tool,
credential, mount, egress, path, or policy authority.

Idempotency and dedup: key by work item, claim key, role, brief hash, and
target branch. Re-dispatch requires an expired, released, or explicitly
superseded claim and must preserve prior evidence rather than replacing it.

### `autoreview-decide`

Purpose: decide whether automated review evidence can be routed, refreshed, or
returned without treating automation as ratification.

Inputs:

- Pull request ref, head SHA, author identity evidence, and requested reviewer
  role.
- Existing review state, review-thread state, CI status, and changed path set.
- Reviewer authority envelope when a reviewer verdict is to be submitted.

Governed steps:

1. Resolve author identity and refuse self-review.
2. Classify whether the review action is advisory evidence, a reviewer verdict,
   or a return-to-author action.
3. Check reviewer authority envelope and active run-mode predicates before any
   verdict submission.
4. Submit or refresh evidence only under the reviewer role; otherwise return a
   no-action explanation.
5. Record stale, superseded, blocked, or changes-requested outcomes.

Classification: mixed. Evidence collection, stale-state detection, and
return-to-author are autonomous. Approval submission requires the reviewer
authority predicates named by ADR-0013. Self-review, missing-envelope approval,
policy exceptions, and merge overrides are reserved or refused.

Idempotency and dedup: key by PR number, head SHA, reviewer role, and verdict
kind. A new head SHA invalidates prior automated evidence; repeated runs on the
same head should update or supersede the prior evidence instead of stacking
duplicate verdicts.

### `trigger-triage-claim`

Purpose: map forge events into claimable work without letting the event itself
authorize mutation.

Inputs:

- Trigger class and source event from the trigger taxonomy.
- Repository, issue or PR identifier, labels, command text when present, and
  event delivery identifier.
- Current active claims, dependency state, and dedup window.

Governed steps:

1. Normalize the trigger into a value-free work proposal.
2. Check dedup keys and suppress repeats inside the active window.
3. Map the proposal to a ready, blocked, reserved, or advisory state.
4. Create or update an advisory claim only when collision predicates pass.
5. Dispatch follow-on workflow only when its own inputs and authority
   predicates hold.

Classification: autonomous for intake, territory mapping, claim-or-skip, and
queue updates. Reserved if the trigger asks for privileged mutation, authority
expansion, release, deploy, policy exception, or ambiguous high-consequence
scope.

Idempotency and dedup: key by event delivery identifier, normalized resource
key, command fingerprint, label state hash, and dedup window. Replayed webhook
deliveries must be recognized as the same proposal.

### `forge-setup-plan-apply`

Purpose: produce and, when ratified, apply a forge-side setup plan for branch
protection, required checks, app permissions, workflow installation, reviewer
identity, and rollback evidence.

Inputs:

- Install contract, target repository facts, setup profile, and plan-tier
  enforceability evidence.
- Current protection, ruleset, workflow, check, reviewer, app permission, and
  rollback snapshots.
- Operator ratification reference for any live forge mutation.

Governed steps:

1. Inventory current forge posture and refuse if preservation facts are absent.
2. Produce a desired-state plan with consequence class, reversibility, rollback
   refs, and no-weaken proof.
3. Stop at plan-only unless live mutation has explicit ratification.
4. Apply desired-state changes idempotently and read back each changed setting.
5. Emit completion evidence, rollback instructions, and residual risks.

Classification: mixed. Inventory, plan generation, readback, and refusal are
autonomous. Live forge settings mutation, credential grants, branch-protection
changes, app installation changes, release, and deploy are reserved.

Idempotency and dedup: key by target repository, install contract hash, desired
setup profile hash, and ratification reference. Apply steps must compare
desired and observed state before mutation and must be safe to re-run after a
partial failure.

### `resource-lock-queue`

Purpose: coordinate advisory locks and priority queues for forge artifacts such
as issues, PRs, branches, workflows, and setup targets.

Inputs:

- Resource key, requested holder, purpose, priority, staleness policy, and
  current lock ledger.
- Dependency state and supersession or takeover evidence when applicable.

Governed steps:

1. Normalize the resource key and classify the requested operation.
2. Check active locks and apply deterministic winner rules.
3. Record acquire, skip, release, stale, supersede, or takeover outcomes.
4. Surface queue state for dispatch and review workflows.
5. Refuse dispatch when the workflow requires a held claim and none exists.

Classification: autonomous for advisory claim management and queue rendering.
Reserved if a takeover would hide evidence, erase history, bypass dependency
order, or grant broader authority than the requested workflow already has.

Idempotency and dedup: key by resource key, holder, purpose, and claim epoch.
Lock operations append state transitions; they must not rewrite prior release
or takeover evidence.

### `workflow-memory-proposal`

Purpose: convert retrospectives and run outcomes into proposed workflow,
prompt, trigger, or guardrail changes without self-mutating the active system.

Inputs:

- Retrospective evidence, run outcome, failure class, affected workflow name,
  and proposed change summary.
- Current catalog entry, prompt refs when present, and guardrail references.

Governed steps:

1. Classify the observation as evidence, draft patch, or no-action note.
2. Link the proposal to the affected workflow and source evidence.
3. Generate a reviewable change proposal without activating it.
4. Route the proposal through normal review and ratification paths.
5. Activate only after the governed artifact change lands through its approved
   path.

Classification: autonomous for collecting evidence and drafting proposals.
Reserved for activating workflow changes, weakening guardrails, changing
authority, broadening tools or credentials, or applying memory automatically.

Idempotency and dedup: key by affected workflow, evidence hash, proposed
change fingerprint, and active proposal state. Repeated retrospectives should
join the existing proposal when the fingerprint matches.

## Global Stop Conditions

All cataloged workflows must stop and report rather than continue when:

- Required inputs are missing or contradictory.
- The requested action moves from autonomous to reserved classification.
- The workflow would broaden path, tool, credential, egress, mount, or policy
  authority beyond the approved envelope.
- Dedup evidence shows the same action already ran for the same key and active
  window.
- The workflow would treat CI, automation, or an app runtime as ratification.
- A runtime implementation would require schema, product code, workflow file,
  broker, or CLI changes not covered by the active slice.
