# Contract: Forge Trigger Taxonomy

**Status:** Draft contract. Documentation-only vocabulary for future
forge-side automation slices. This document does not add runtime enforcement,
webhook handling, workflow wiring, repository mutation tooling, credential
grants, or validator behavior.

## Purpose

The forge trigger taxonomy names the forge events a future governed executor
may observe and maps each event to a bounded response class. The contract is
vocabulary-first: it defines trigger keys, event families, preconditions,
guardrails, and evidence outputs so later implementation slices can share a
stable language without expanding authority.

Triggers can make work visible, propose next actions, enqueue governed work,
route attention, request review, or emit evidence. A trigger does not approve,
merge, ratify, mutate repository or provider settings, mint credentials,
bypass checks, change branch protection, or authorize privileged action.

## Response Classes

Every trigger maps to one or more response classes below. The classes are
intentionally narrow.

| Response class | Meaning | Authority boundary |
| --- | --- | --- |
| `advisory` | Report a condition, suggested interpretation, or next step. | Read-only. No mutation is authorized. |
| `propose` | Produce a candidate action for a governed actor to approve or reject. | The proposal is inert until separately authorized. |
| `enqueue` | Add or refresh a candidate work item in a governed queue. | Queue visibility is not implementation authority. |
| `route` | Direct attention to the appropriate role, lane, or queue. | Routing does not assign privileged capability. |
| `review` | Request or schedule review activity subject to author-reviewer separation. | Review may inspect and comment; it cannot self-approve or merge. |
| `evidence` | Record deterministic observations, hashes, links, timestamps, or refusal reasons. | Evidence supports later decisions but never ratifies them. |

## Global Preconditions

A trigger is eligible for response only when all applicable conditions hold:

- the event is from an allowed repository, project, workflow, or queue surface;
- the event payload can be normalized into the trigger key's canonical fields;
- the actor, branch, issue, pull request, check, or queue item can be identified
  without guessing;
- the dedup key can be computed from deterministic evidence;
- the response class is available to the observing role;
- the response does not require absent tools, elevated credentials, network
  egress, or live settings mutation;
- author-reviewer separation is preserved for review and approval flows; and
- any existing resource claim or advisory lock is re-read immediately before a
  conflicting recommendation is emitted.

If a precondition is missing, the governed response is `evidence` with a refusal
or escalation proposal, not best-effort actuation.

## Dedup and Idempotency

Each trigger response MUST derive a deterministic dedup key from stable
evidence. The minimum shape is:

```text
trigger_key + repository + subject_type + subject_id + normalized_event_kind + evidence_hash + window
```

The `window` value depends on the trigger:

- `instant`: one event delivery or one canonical payload hash;
- `short`: a burst window for duplicate edits, repeated comments, retries, or
  synchronized status updates;
- `queue`: a merge queue or required-check state epoch;
- `lease`: a resource claim, lock, or handoff window; and
- `retrospective`: a bounded workflow-memory proposal period.

Retries with the same dedup key refresh evidence rather than producing a second
candidate action. A changed payload hash or changed governing state starts a new
candidate only when the trigger key permits it.

## Authority and Non-Ratification

The taxonomy separates observation from authority:

- **Advisory vs actuating.** All responses are advisory, proposal, queue,
  routing, review, or evidence outputs. A future executor may create those
  outputs only inside its separately granted scope. The output itself does not
  perform the proposed action.
- **Reserved vs autonomous.** Reserved triggers require explicit Operator or
  governed actor approval before any downstream mutation. Autonomous triggers
  may only refresh advisory/evidence/queue state.
- **Privileged surfaces.** GitHub or provider settings, app grants, workflow
  files, branch protection, deploy configuration, merge gates, PR approval,
  credentials, and live repository administration are reserved. Trigger
  observation cannot authorize those surfaces.
- **CE-event blocks.** CE-event blocks are append/read evidence and routing
  substrate. They cannot ratify privileged authority, approve a PR, merge code,
  mutate settings, or waive checks.
- **Credential and egress posture.** Trigger processing is deny-by-default for
  secrets and network egress. A trigger may record missing access as evidence
  and may propose escalation; it must not mint or request credentials on its own.
- **Locks and resource claims.** Locks are advisory unless a future slice
  explicitly provides an atomic primitive. Any contention is surfaced as
  evidence and escalation, not silently overwritten.

## Trigger Table

The table is the canonical vocabulary. `Reserved` means the trigger can only
propose, route, review, enqueue, or emit evidence for a human or governed actor
to decide. `Autonomous` means the trigger may update advisory/evidence/queue
state within its separately granted scope.

| Trigger key | Event family | Governed response | Preconditions | Refusal and guardrails | Evidence outputs |
| --- | --- | --- | --- | --- | --- |
| `issue.opened` | Issue lifecycle | `enqueue`, `route`, `evidence` | Issue payload includes repository, issue number, title, body hash, actor, labels, and timestamp. | Autonomous for queue visibility only. Must not assign implementation authority or edit the issue. | Normalized issue identity, body hash, label snapshot, duplicate-search inputs. |
| `issue.edited` | Issue lifecycle | `advisory`, `propose`, `evidence` | Edited fields and before/after body hashes are available. | Refuse if the edit changes scope but no governed actor has confirmed the new intent. | Changed-field list, old/new hashes, affected queue candidates. |
| `issue.labeled` | Issue lifecycle | `route`, `enqueue`, `evidence` | Label exists on the repository and maps to a known routing or readiness meaning. | Unknown or privileged labels are evidence only. Labels do not authorize implementation. | Label name, label source, routing interpretation, queue key. |
| `issue.assigned` | Issue lifecycle | `advisory`, `evidence` | Assignee and issue identity are known. | Assignment is not an atomic lock and cannot override an existing claim. | Assignee snapshot, claim comparison, contention note if any. |
| `pr.opened` | PR lifecycle | `route`, `review`, `evidence` | PR head/base, author, changed-path summary, body hash, and work-class declaration are readable. | Reserved for review routing. Must not approve, merge, retarget, or mutate branch protection. | PR identity, author, base/head refs, body hash, path summary. |
| `pr.synchronize` | PR lifecycle | `review`, `evidence` | New head SHA, prior head SHA, and changed-path summary are readable. | Must invalidate stale advisory conclusions tied to the old SHA. Must preserve author-reviewer separation. | Old/new SHA pair, changed files, stale-evidence references. |
| `pr.reopened` | PR lifecycle | `route`, `review`, `evidence` | PR state transition and current head SHA are readable. | Reopen does not restore prior approvals or review conclusions as ratifying evidence. | Reopen timestamp, actor, head SHA, previous state. |
| `pr.ready_for_review` | PR lifecycle | `route`, `review`, `evidence` | Draft-to-ready transition and requested reviewers are readable. | Must not auto-assign a self-reviewing author. | Ready timestamp, reviewer routing proposal, separation check. |
| `pr.review.submitted` | PR review | `route`, `evidence` | Review state, reviewer, submitted SHA, and review body hash are readable. | Review submission is evidence only; it cannot merge or override required checks. | Review ID, reviewer, state, submitted SHA, body hash. |
| `pr.review.changes_requested` | PR review | `route`, `enqueue`, `evidence` | Requested-changes review is tied to a PR SHA and reviewer identity. | Must not dismiss, resolve, or bypass requested changes. | Review URL, blocking reason summary, author-notification route. |
| `pr.review.approved` | PR review | `evidence` | Approver differs from author and approval is tied to the current head SHA. | Approval evidence cannot merge, ratify privileged authority, or waive checks. Stale or self approvals are refusal evidence. | Approval reviewer, head SHA, separation result, staleness result. |
| `pr.review.commented` | PR review | `route`, `evidence` | Comment body hash, file/thread identity when present, and commenter are readable. | Comments are non-ratifying and cannot be interpreted as approval unless the review state says so. | Comment hash, thread identity, mention/command extraction. |
| `comment.command.done` | Comment command | `propose`, `route`, `evidence` | Command syntax, actor, subject, and target work item are unambiguous. | Reserved. May propose completion evidence only; must not close, merge, or mark done without separate authority. | Parsed command, actor, subject, proposed completion evidence. |
| `comment.command.blocked` | Comment command | `route`, `evidence` | Blocker text or linked blocker is present. | Must not abandon or close work. Route to triage or escalation. | Blocker statement hash, linked issue/PR, escalation route. |
| `comment.command.escalate` | Comment command | `route`, `evidence` | Escalation target or reason can be parsed. | Must not grant extra authority. Escalation is visibility only. | Reason hash, target role/queue, source comment URL. |
| `comment.command.handoff` | Comment command | `propose`, `route`, `evidence` | Source actor, target actor/role, scope, and handoff evidence are present. | Reserved when handoff would change authority, credentials, or live settings. | Handoff scope, target, evidence bundle hash. |
| `comment.mention` | Comment mention | `route`, `evidence` | Mentioned role or actor maps to a known route. | Unknown mentions are evidence only. Mentions do not create assignment authority. | Mention target, source comment hash, route proposal. |
| `checks.completed` | Check suite/run/status | `route`, `evidence` | Check name, conclusion, status, SHA, provider, and required/non-required classification are readable. | Must not rerun, override, or mark checks successful. Provider settings mutation is reserved. | Check identity, conclusion, SHA, required flag, log URL when available. |
| `required_check.state_changed` | Required-check state | `advisory`, `route`, `evidence` | Required-check set and current PR SHA can be read from an authorized source. | Required-check interpretation is evidence only; cannot waive branch protection or merge gates. | Required set snapshot, per-check state, source timestamp. |
| `merge_group.checks_requested` | Merge queue | `route`, `evidence` | Merge group SHA, base branch, queue position or group identity, and requested checks are readable. | Must not enqueue/dequeue, reorder queue, or merge. | Merge group identity, requested checks, queue epoch. |
| `merge_queue.state_changed` | Merge queue | `advisory`, `route`, `evidence` | Queue item identity and state transition are readable. | Queue state does not authorize merge or bypass checks. | Queue state snapshot, transition timestamp, affected PRs. |
| `branch.created` | Branch/ref | `advisory`, `evidence` | Ref name, target SHA, actor, and repository are readable. | Must not delete, protect, rename, or retarget refs. | Ref name, target SHA, actor, naming-policy advisory result. |
| `branch.deleted` | Branch/ref | `evidence` | Deleted ref name and prior SHA are available from the event. | Must not recreate refs. Missing prior SHA is refusal evidence. | Ref deletion event, prior SHA if available, affected open PRs. |
| `ref.force_pushed` | Branch/ref | `route`, `evidence` | Before/after SHAs and ref name are readable. | Must not reset, revert, or rewrite refs. Route for review invalidation only. | Before/after SHAs, affected PRs, invalidated evidence IDs. |
| `workflow_run.completed` | Workflow run | `route`, `evidence` | Workflow name, run ID, conclusion, head SHA, and artifact/log links are readable. | Must not rerun, edit workflows, or treat workflow success as ratification. Workflow-file mutation is reserved. | Run ID, conclusion, head SHA, artifact/log references. |
| `schedule.tick` | Schedule | `advisory`, `enqueue`, `evidence` | Schedule identity, intended scope, and last successful tick are known. | Autonomous only for advisory scans and queue refresh. Must not mutate live settings or start privileged work. | Tick ID, scope, dedup window, scan summary. |
| `webhook.delivery` | Webhook delivery | `evidence` | Delivery ID, event type, payload hash, receipt time, and verification status are available. | Failed verification is refusal evidence. Delivery does not authorize payload action by itself. | Delivery ID, verification result, payload hash, normalized trigger candidates. |
| `webhook.retry` | Webhook delivery | `evidence` | Original delivery ID or payload hash can be linked to the retry. | Retry must reuse dedup state and must not duplicate candidate actions. | Original/retry IDs, payload hash, retry count. |
| `delay.window_elapsed` | Time window | `advisory`, `route`, `evidence` | Window key, start time, elapsed time, and subject state are known. | Window expiry can surface staleness but cannot close, merge, or abandon work. | Window key, elapsed duration, current subject state. |
| `dedup.window_closed` | Time window | `evidence` | Candidate set and deterministic dedup keys are available. | Must not discard non-duplicate work without evidence. | Candidate keys, retained candidate, duplicate evidence hashes. |
| `retrospective.proposed` | Retrospective | `propose`, `evidence` | Proposal text hash, source evidence, and affected workflow artifact are known. | Reserved. Must not self-mutate workflow memory, workflow files, settings, or branch protection. | Proposal hash, source evidence links, affected artifact path. |
| `workflow_memory.proposed` | Retrospective | `propose`, `evidence` | Memory proposal includes scope, source evidence, and rollback/removal path. | Reserved. A proposal cannot install itself or become policy without separate ratification. | Memory proposal hash, source evidence, requested reviewer route. |
| `manual.operator.done` | Manual command | `propose`, `evidence` | Operator identity, subject, exact done criteria, and evidence bundle are present. | Reserved when completion would close issues, merge PRs, or change queue status. | Command hash, subject, criteria, evidence bundle hash. |
| `manual.operator.blocked` | Manual command | `route`, `evidence` | Operator identity, subject, and blocker reason are present. | Must not mutate assignments or close work unless separately authorized. | Blocker reason hash, route target, affected work items. |
| `manual.operator.escalate` | Manual command | `route`, `evidence` | Operator identity, escalation reason, and requested target are present. | Escalation does not expand credentials or permissions. | Escalation reason hash, target, source command. |
| `manual.operator.handoff` | Manual command | `propose`, `route`, `evidence` | Operator identity, source, target, scope, and handoff evidence are present. | Reserved for any authority-bearing handoff. Must not transfer credentials. | Handoff scope hash, source/target, evidence bundle. |

## Reserved Surfaces

The following surfaces are always reserved. A trigger may produce evidence or a
proposal about them, but cannot execute or ratify the underlying action:

- approving, dismissing, or requesting changes on a PR;
- merging, enqueueing into a protected merge path, dequeueing, or bypassing
  required checks;
- creating, rotating, reading, or distributing credentials;
- changing GitHub App grants, repository settings, branch protection,
  environments, deployments, secrets, workflow files, or CI provider settings;
- deleting, force-updating, or protecting refs;
- changing live forge settings, project configuration, labels, milestones, or
  issue templates;
- self-modifying workflow memory, policy, or automation rules; and
- treating CE-event blocks, comments, labels, or check results as ratification.

## Future Executor Contract Requirements

A future executor that implements this taxonomy MUST:

- preserve these trigger keys or declare a versioned migration table;
- emit the response class, dedup key, evidence hash, and refusal reason for
  every observed trigger candidate;
- keep privileged surfaces reserved unless a separate contract grants the exact
  authority and records its ratification path;
- enforce author-reviewer separation for review routing;
- re-read current state before surfacing lock, claim, required-check, or queue
  advice;
- treat missing tools, missing credentials, unavailable egress, and ambiguous
  payloads as refusal evidence; and
- keep event append/read evidence separate from authority and mutation paths.

## Non-Goals

This document does not define a webhook receiver, scheduler, queue adapter,
GitHub App permission set, check rerunner, merge controller, credential broker,
workflow-memory writer, or validator check. Those require separately governed
slices with explicit scope and authority.
