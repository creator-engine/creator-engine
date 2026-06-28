# CE Orchestrator Agent

**Status**: Design-only proposal. No implementation is authorized by this
document.

**Scope**: Canonize the CE Orchestrator Agent role currently performed
ad hoc by CE-DEV-2: coordination, supervision, and management of the
governed development fleet.

**Non-goals**: This document does not change product code, validators,
runtime policy, worker role files, carrier files, changelog entries,
`AGENTS.md`, `CLAUDE.md`, or `.claude/agents/*`.

## Problem and Product Thesis

Creator Engine already operates as a small governed development company:
intake is decomposed into tickets, tickets are dispatched to specialized
seats, work is harvested, independently reviewed, gated, merged, and
then pulled forward into the next lane. The missing product artifact is
the agent that owns that whole conveyor.

Today the Orchestrator role exists as practice rather than product. It
is distributed across CE-DEV-2 memory, resume-state checkpoints, controller
playbooks, bootstrap previews, worker role definitions, and ad hoc seat
discipline. That makes the role effective but not shippable: a new
controller can imitate parts of it, but the contract is not compact,
deterministic, testable, or operator-visible.

The product thesis is: **CE should ship a governed Orchestrator Agent
whose job is not to write code, but to keep a fleet of governed workers
moving through a visible, auditable delivery conveyor.** It should behave
like a controller/foreman with a merge gate, not like a general coding
assistant with more tools.

## Current Evidence and Gaps

Strong in-repository evidence exists for the core role contract:

- `docs/design/controller-bootstrap-ssot.json` defines the controller
  foreman directive: plan, dispatch, monitor, triage, delegate substantive
  work, preserve author/reviewer separation, avoid inline implementation,
  and respect worktree ownership.
- `docs/design/controller-bootstrap-injection.md` defines the SSOT as a
  preview-only deterministic bootstrap source and explicitly refuses live
  mutation of `AGENTS.md`, `CLAUDE.md`, and `.claude/agents/*`.
- `playbooks/controller/workflow.ce.yml` and its briefs define dispatch
  and merge-gate actions. Merge requires independent review, green
  validation, and ratification.
- `specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`
  defines role-shaped worker policies for `architect_research`,
  `implementer`, and `verification`.
- `.claude/agents/README.md` and the role files define governed worker
  behavior and the reviewer specialization.
- Root-checkout resume-state checkpoints at
  `/home/ce-dev-1/creator-engine/.ce/state/research/RESUME_STATE_CE_DEV2_*`
  ground the operating practice that this design productizes: G1-G5 live
  grants and R-reserved HALT snapshots, night conveyor cadence, no-forks
  restricted-agent discipline, verify-before-dispatch, territory-map checks,
  context gates, contained dispatch mechanics, harvest/fan-in mechanics, and
  the CEO-mode shift.

Important gaps remain:

- The exact ADR draft path named in the seed brief,
  `.ce/state/research/ADR_DRAFT_substrate_independent_authority_20260628.md`,
  is absent from this checkout.
- `.ce/state/research/PETER_STEINBERGER_AUTONOMY_ANALYSIS_20260627.md`
  is absent from this checkout. The resume-state checkpoint
  `RESUME_STATE_CE_DEV2_DAYARC_20260627T0600Z` summarizes its thesis as
  run-mode, not tooling: shift from `skynet x Dev` to `skynet x CEO`, with
  throughput leading while governance catches up and the first live flip
  reserved to the Operator.
- `.claude/skills/ce-dispatch/SKILL.md` and a dedicated `ce-harvest` skill
  are not live in this checkout. They should be productization slices or
  pointers to tracked dispatch and harvest playbooks, not assumed existing
  in-tree authorities.
- The controller-bootstrap SSOT is preview-only. It is a codified
  knowledge seam, not yet live bootstrap injection.
- Substrate-independent authority is grounded at the contract level here, but
  the detailed authority-substrate ADR still needs tracked recovery.

## Orchestrator Contract

The Orchestrator Agent owns a lifecycle, not an implementation task.

### Lifecycle

1. **Intake**: accept an Operator request, issue, PR state, or conveyor
   signal; identify objective, stop line, authority class, and known
   dependencies.
2. **Territory map**: inspect active claims, in-flight PRs, briefs,
   worktrees, path manifests, and branch state. Refuse or reroute work
   that collides with another seat.
3. **Dispatch**: create a self-contained governed-seat brief naming the
   ticket, branch, role, allowed paths/surfaces, expected evidence,
   validation bar, and stop line. Dispatch by pointer plus hash when the
   brief is long. Record or verify the work claim before the worker starts.
4. **Progress/stall watch**: monitor liveness, context pressure, CI,
   branch drift, stop-line output, worker stalls, and dependency changes.
   Refresh or split work when the current seat is no longer the best
   execution surface.
5. **Harvest**: collect worker output at READY/stop-line, verify the
   claimed scope, inspect changed files, and stage the branch or artifact
   without broadening the worker's authority.
6. **Independent review**: route authored work to a distinct reviewer or
   verification lane. Reviewer evidence is advisory unless it satisfies
   the merge-gate policy.
7. **Gate/merge**: hold the merge gate. Merge only when independent review,
   green validation, declared work class, ratification, and applicable
   grant conditions are all satisfied.
8. **Conveyor next lane**: immediately select the next ready work item or
   unblock the next lane. The Orchestrator should not idle while ready,
   unclaimed, unblocked work exists.
9. **Checkpoint**: write enough state for another controller to resume:
   current lane, active workers, claims, branch/PR status, blockers,
   Operator decisions needed, and next recommended actions.

### State Machine

```text
INTAKE
  -> MAP_TERRITORY
  -> CLAIM_OR_SKIP
  -> DISPATCH
  -> WATCH
  -> HARVEST
  -> VERIFY_AND_REVIEW
  -> GATE
  -> MERGED_OR_RETURNED
  -> CHECKPOINT
  -> NEXT_LANE
```

`RETURNED` routes back to `DISPATCH` with a narrower fix brief. `BLOCKED`
routes to `CHECKPOINT` plus an Operator decision request. `HALT` stops the
lane until a reserved authority is supplied.

### Inputs and Outputs

Primary inputs:

- Operator objective, issue, PR, or conveyor signal.
- Forge state: issues, PRs, reviews, CI, labels, branches, comments, and
  existing locks.
- Repository state: base/head, changed paths, worktree cleanliness,
  manifests, playbooks, specs, and bootstrap SSOT.
- Fleet state: seat capabilities, containment status, current task,
  context pressure, liveness, and harvest readiness.
- Company brain/recall assertions where present, treated as hints until
  verified against the repo or forge.

Primary outputs:

- Work claim or explicit skip reason.
- Dispatch brief with role, scope, evidence, and stop line.
- Progress/stall note or refresh instruction.
- Harvest report with changed paths and validation evidence.
- Review-routing request and review evidence.
- Gate decision with explicit satisfied/missing predicates.
- Operator decision request when autonomy ends.
- Checkpoint/resume state.

### Invariants

- The Orchestrator does not perform substantive implementation or full
  review inline when governed workers are available.
- Every dispatched unit has one role, one worktree/branch envelope, and a
  stop line.
- Author and reviewer are distinct.
- Work is file-territory-aware before dispatch and before merge.
- Merge requires independent review, green validation, and ratification.
- Worker authority is role-shaped by mount, egress, and credential policy,
  not by prompt wording alone.
- Reserved actions halt until the Operator supplies authority.
- The conveyor keeps moving after closeout; idle seats are a fault to be
  triaged, not a steady state.

## Decision and Authority Model

The Orchestrator needs a simple split: autonomous delivery decisions are
allowed inside grants; governance, irreversible, or high-consequence
decisions escalate.

### Autonomous Decisions

The Orchestrator may decide to:

- pick the next unclaimed, unblocked, dependency-ready ticket;
- skip a locked or blocked ticket with a recorded reason;
- decompose work into file-disjoint dispatches;
- choose `architect_research`, `implementer`, `verification`, or reviewer
  specialization based on task shape;
- choose model/effort routing within current policy;
- rerun transient checks or request a worker fix when the evidence is clear;
- harvest a worker result that matches its brief and stop line;
- open or update ordinary delivery PRs when the applicable grant permits it;
- continue the conveyor after merge or return-to-author.

### Escalation Decisions

The Orchestrator must surface an Operator decision when:

- scope is new, ambiguous, or high-consequence;
- the requested action is R-reserved/HALT;
- the lane requires release, sign, publish, deploy, fleet rollout/arming,
  history scrub, weakening guards, irreversible destructive work, or a new
  policy exception;
- direct evidence conflicts with remembered or recalled state;
- the Orchestrator would need to broaden worker credentials, mounts, egress,
  or path authority beyond the dispatched envelope;
- merge predicates are missing but there is pressure to proceed;
- the first live auto-merge flip or equivalent governance escalation is
  requested.

### Grants and Reserves

The root resume-state checkpoints say G1-G5 autonomous grants are live, while
R-reserved items remain HALT. The continuation brief names ADR-0013 as the
substrate-independent authority source, but no tracked ADR-0013 file or
authority ADR draft is present in this checkout. This document therefore
canonizes the model at the contract level and marks precise grant text and
substrate details as a follow-up inventory.

| Band | Contract | Current design stance |
|---|---|---|
| G1 | Merge-gate grant | Autonomous merge may proceed only when the baseline is clean, carrier/preflight passes, work is in-arc, declared work class is present, required CI is green, the branch was never red under the relevant grant, independent review exists, and ratification is satisfied. |
| G2 | Dispatch/claim grant | Autonomous claim and worker dispatch are allowed for unblocked, unlocked, dependency-ready work with file-territory checks and visible claim comments. |
| G3 | Validation/retry grant | Autonomous local preflight, CI inspection, transient rerun, and return-to-author loops are allowed when they do not broaden scope or credentials. |
| G4 | Harvest/fan-in grant | Autonomous harvest of contained or non-contained worker results is allowed when output matches the brief, changed paths are in scope, and evidence is preserved. |
| G5 | Conveyor/queue grant | Autonomous pull-forward, batch dispatch, and next-lane routing are allowed when dependency order, author/reviewer separation, and file-disjointness hold. |
| R-reserved | HALT/reserve | Release, sign, publish, deploy, fleet rollout/arming, history scrub, weakening guards, irreversible destructive work, and new high-consequence scope require Operator authority. |

Authority is **substrate-independent**: the same decision contract should hold
whether the acting surface is a Codex seat, Claude-Code pane, server-side
agent runtime, GitHub App, local CLI, or future CEO-mode cockpit. The
substrate may change how actions are executed, but not who may decide them,
what predicates must be true, or which actions are reserved.

## Worker and Seat Model

The Orchestrator drives governed seats with role-shaped authority.

| Role | Default use | Authority shape |
|---|---|---|
| `architect_research` | Repository reading, architecture, option analysis, reproduction planning, external research, and implementation briefing. | Read-only worktree/governance mounts, model-provider and ratified docs/source-host read egress, no write token. |
| `implementer` | Scoped source/docs edits inside one allocated worktree and branch. | Read-write only in the delegated worktree/path envelope, task-scoped source-host credential, no approval/merge authority. |
| `verification` | Tests, builds, validator replay, CI log review, evidence validation. | Read-only source plus writable scratch/build output, no egress by default, no credentials by default. |
| `reviewer` | Harness/schema review specialization mapped to `verification`. | Read-only review verdict/evidence only; controller submits any forge-side review action. |

Routing rules:

- Start with `architect_research` when the problem is unclear, high-risk, or
  needs discovery.
- Use `implementer` only after scope, allowed paths, validation, and stop line
  are concrete.
- Use `verification` for check replay and evidence collection.
- Use `reviewer` for non-author PR review semantics; keep it distinct from
  the authoring worker.
- Prefer the least-authority role that can complete the work.
- Split mixed build/review tasks. Do not let a worker silently change roles.

Model and effort routing:

- Use cheaper/fast execution for bounded claim checks, carrier regeneration,
  status polling, and already-specified docs edits.
- Use higher-reasoning research lanes when the Orchestrator must reconcile
  conflicting evidence, plan cross-ticket decomposition, or judge ambiguous
  authority.
- Treat model selection as an execution detail inside the current grant. It
  must not broaden mounts, credentials, egress, or action authority.
- Preserve the same evidence bar regardless of model: changed paths,
  validation output, review routing, and gate predicates must be recorded.

Current seat pattern:

- CE-DEV-1 style seats may be non-contained and can self-push within grant.
- CE-DEV-3/CE-DEV-4 style seats may be contained and need harvest fallback or
  courier mechanics for forge side effects.
- The Orchestrator dispatches self-contained briefs and avoids inline work.
- Multi-ticket batch dispatch is permitted only after checking path
  disjointness against other seats and in-flight PRs.

Harvest mechanics:

- The worker declares READY or reaches its stop line.
- The Orchestrator verifies branch, diff, declared changed paths, and evidence.
- Contained-seat output is harvested through a staging worktree or equivalent
  fan-in packet; non-contained output can be self-pushed if grant conditions
  permit.
- Harvest does not imply merge readiness. It feeds independent review and
  gate validation.

## Knowledge Substrate and Deterministic Bootstrap

The Orchestrator must load operating knowledge deterministically. Recall is
useful but cannot be the authority source.

Knowledge layers:

1. **Tracked SSOT**: `docs/design/controller-bootstrap-ssot.json` is the
   current codified knowledge seam for controller behavior, roles, routing,
   pre-dispatch checks, harvest sequence, model routing, and safety floor.
2. **Preview generator**: `scripts/gen-controller-bootstrap.py` validates and
   renders bootstrap previews, while refusing live `AGENTS.md`, `CLAUDE.md`,
   and `.claude/agents/*` outputs.
3. **Playbooks**: `playbooks/controller/` defines dispatch, merge-gate,
   seat-refresh, and courier operation behavior.
4. **Skills**: `ce-dispatch` and `ce-harvest` are not live in this checkout.
   Productization should add pointer skills to tracked dispatch and harvest
   playbooks after those pointers are ratified.
5. **Company brain/recall**: stores fleet conventions, current capabilities,
   and operating memories. It is a recall substrate, not a decision authority.
6. **Resume/checkpoint state**: the active controller must emit resumable
   state so the next controller can continue without memory-only transfer.
   Current design grounding comes from the root checkout's CE-DEV-2
   resume-state checkpoints.

The productized Orchestrator should boot by loading the SSOT, validating its
version/hash, loading relevant playbooks/skills, then checking live forge and
worktree state. It should not start from memory and only later reconcile
against state.

## Cadence, Monitoring, and Checkpointing

The Orchestrator operates a harvest-monitor loop:

1. Verify candidate work is not already done.
2. Check territory, dependency order, and work claim status.
3. Dispatch with evidence requirements and stop line.
4. Monitor liveness, context pressure, branch drift, CI, and worker output.
5. Harvest at stop line or READY.
6. Run preflight or equivalent validation on a clean tree.
7. Open/update PR, route independent review, and gate merge.
8. Feed the next lane immediately after closeout.

Night cadence from the root resume-state checkpoints should be productized as
scheduled jobs:

- `poll-devs :05`: collect seat liveness, stop lines, and blockers.
- `conveyor-tend :30`: move ready harvested work through review/gate/next lane.
- `belt 5m`: scan for ready work, stale locks, and unclaimed conveyor items.
- `seat-check :00`: inspect context pressure, stale panes, and refresh needs.
- `context-gate before dispatch`: avoid sending a seat into new work when its
  context pressure makes a clean restart safer.

Checkpoint records should include:

- active objective and issue/PR links;
- current lifecycle state;
- active claims and locks;
- workers, roles, branches, worktrees, containment mode, and expected stop line;
- changed-path territory and collision notes;
- validation/review/gate status;
- Operator decisions requested or resolved;
- next action if the controller disappears.

### Runtime Record Schemas

These are design-level shapes, not implementation schemas. Future slices
should promote them to versioned records with validation and migration rules.

Checkpoint record:

```yaml
kind: ce-orchestrator-checkpoint
version: 1
checkpoint_id: string
created_at: timestamp
controller_id: string
objective: string
lifecycle_state: INTAKE | MAP_TERRITORY | DISPATCH | WATCH | HARVEST | VERIFY_AND_REVIEW | GATE | CHECKPOINT | NEXT_LANE | BLOCKED | HALT
refs:
  issues: [string]
  prs: [string]
  branches: [string]
active_claims:
  - claim_ref: string
    worker_id: string
    role: architect_research | implementer | verification | reviewer
    branch: string
    worktree: string
    containment: contained | non_contained
    stop_line: string
territory_map_ref: string
gate:
  validation: unknown | pending | green | red
  independent_review: missing | pending | satisfied | changes_requested
  declared_work_class: tiny | story | feature | epic | unknown
  ratification: missing | satisfied | not_required
operator_decisions: [string]
next_action: string
```

Territory-map record:

```yaml
kind: ce-orchestrator-territory-map
version: 1
map_id: string
created_at: timestamp
base_ref: string
entries:
  - path_pattern: string
    owner_worker: string
    issue_ref: string
    pr_ref: string
    branch: string
    claim_ref: string
    lock_status: clear | locked | stale | contested
    changed_paths: [string]
collision_checks:
  - candidate_ref: string
    result: clear | collision | blocked
    reason: string
```

Harvest-packet record:

```yaml
kind: ce-orchestrator-harvest-packet
version: 1
packet_id: string
worker_id: string
role: implementer | verification | architect_research | reviewer
brief_ref: string
brief_sha256: string
branch: string
base_ref: string
head_sha: string
changed_paths: [string]
diff_summary: string
evidence:
  validation_commands: [string]
  validation_result: pass | fail | not_run
  artifacts: [string]
stop_line_result: ready | blocked | returned | superseded
scope_verdict: in_scope | out_of_scope | needs_controller_review
```

Operator-decision queue record:

```yaml
kind: ce-orchestrator-operator-decision
version: 1
decision_id: string
created_at: timestamp
requested_by: string
authority_basis: G1 | G2 | G3 | G4 | G5 | R-reserved | unknown
request: string
options:
  - id: string
    label: string
    consequence: string
recommended_option: string
halt_until_resolved: true
resolution:
  status: pending | approved | rejected | superseded
  resolved_by: string
  resolved_at: timestamp
  notes: string
```

## Operator UX, CEO-Mode, and strangeLoop

The Operator should see a fleet-level cockpit, not a transcript dump.

Required surfaces:

- intake queue with dependency and claim status;
- active territory map by path, branch, PR, issue, and worker;
- seat board with role, containment mode, task, liveness, context pressure,
  stop line, and current blocker;
- harvest queue with diff summary and validation evidence;
- review/gate queue showing independent review, CI/preflight, work class,
  ratification, and missing predicates;
- HALT panel for R-reserved decisions, with concrete choices and consequences;
- conveyor next-lane recommendations.

CEO-mode / `strangeLoop` composition:

- CEO-mode is a run-mode shift from hands-on dev control to throughput
  leadership: "skynet x Dev" becomes "skynet x CEO." The Orchestrator
  prioritizes fleet throughput while governance catches up one step behind.
- CEO-mode does not weaken R-reserved boundaries. The first live auto-merge
  flip remains Operator-reserved.
- `strangeLoop` currently affects reviewer independence and review topology,
  not privileged action. It can help form independent review loops, but it
  must not mint approval, merge, release, or publish authority.
- The cockpit/CEO journey should remain a read-only L2 snapshot surface until
  actuator authority is separately ratified.

## Productization Architecture and Path

The shippable Orchestrator Agent should graduate through four layers.

### Layer 1: Canonical Contract

Produce and ratify the Orchestrator role contract: lifecycle, authority,
worker routing, cadence, checkpoints, and acceptance criteria. This document
is the seed.

### Layer 2: Deterministic Knowledge Loading

Extend the controller-bootstrap overlay so the Orchestrator contract is a
first-class SSOT section. Add productized skill pointers for dispatch and
harvest that reference tracked playbooks rather than untracked practice.
Ensure bootstrap preview output can render Orchestrator-specific runbooks
without touching live harness files.

### Layer 3: Runtime State and Observability

Model Orchestrator state as explicit records: claims, dispatches, progress
events, harvests, review requests, gate decisions, checkpoints, and
Operator-decision requests. Build read-only cockpit views first.

### Layer 4: Governed Actuation

Wire actions behind existing grants: claim, dispatch, harvest, review route,
preflight, PR update, and merge gate. Keep R-reserved actions as explicit
Operator-blocking prompts. Only after this layer is proven should CEO-mode
actuators be considered.

### Layer 5: Evals and Trace Review

Add trace-review and evaluation coverage before broad actuation. Required
scenarios include stale worker liveness, context-pressure refresh, path
collision, missing independent review, red CI, dirty checkout, missing
declared work class, R-reserved action request, contained harvest fan-in, and
conveyor pickup after closeout. Each trace should name the grant considered,
the evidence inspected, the decision made, and the next lane selected or
blocked.

The OpenAI Agents SDK is a good fit when CE wants server-owned orchestration,
tool execution, approvals, state, observability, and eval loops. CE can still
preserve substrate-independent authority by making the SDK one execution
substrate, not the source of governance truth.

## Risks and Open Questions

- **Grant precision**: G1-G5 need a tracked authority inventory sourced from
  the root resume-state checkpoints, recovered authority snapshots, and the
  still-missing ADR, then reconciled with current playbooks.
- **Memory drift**: company brain recall can speed orchestration but must not
  override repository or forge evidence.
- **Over-automation**: CEO-mode pressure could turn "keep the conveyor moving"
  into "skip governance." The HALT panel must make reserves visible and hard.
- **Review independence**: `strangeLoop` can improve review topology, but it
  must not blur author/reviewer separation.
- **Contained harvest fidelity**: harvest needs a first-class skill/playbook
  and eventually structured records so output is not lost or filtered through
  a controller summary.
- **Batch dispatch collisions**: file-disjointness must be checked against
  live claims and PRs, not inferred from issue titles.
- **Substrate differences**: Codex, Claude-Code, local CLI, GitHub App, and
  future server runtimes expose different mechanics. Authority must remain
  above those mechanics.
- **Cockpit as actuator**: read-only status is safe; action buttons need
  separate grants and audit records.

## Proposed ce-ops Epic

Epic title: **ce-ops: Productize the Governed CE Orchestrator Agent**

Goal: convert CE-DEV-2's ad hoc controller behavior into a deterministic,
observable, governed Orchestrator Agent with clear authority boundaries and a
path to CEO-mode composition.

| Order | Ticket | Scope | Depends on |
|---|---|---|---|
| 1 | Canonize Orchestrator role contract | Ratify lifecycle, invariants, state machine, inputs/outputs, and non-goals. | This design |
| 2 | Inventory G1-G5 and R-reserved authority | Recover exact grant text from root resume states/authority snapshots; produce a tracked authority matrix and note absent ADR evidence. | 1 |
| 3 | Add Orchestrator section to controller-bootstrap SSOT | Extend the preview-only SSOT with Orchestrator lifecycle, cadence, decisions, and checkpoint schema pointers. | 1, 2 |
| 4 | Productize dispatch/harvest skill pointers | Create ratified `ce-dispatch` and `ce-harvest` pointers to tracked playbooks and pointer+hash mechanics. | 3 |
| 5 | Specify Orchestrator checkpoint record | Design a structured checkpoint/resume record for active objective, workers, claims, blockers, gate state, and next action. | 1 |
| 6 | Specify fleet territory map record | Define read-only records/views for active claims, branches, PRs, changed paths, locks, and collision checks. | 5 |
| 7 | Specify harvest/fan-in packet | Define a durable packet for contained and non-contained worker output: branch, diff, changed paths, evidence, validation, and stop-line result. | 4, 5 |
| 8 | Specify Operator decision queue | Design the HALT/R-reserved decision surface with options, consequences, authority basis, and resolution records. | 2, 5 |
| 9 | Build read-only Orchestrator cockpit | Render intake, territory, seats, harvest queue, review/gate queue, and Operator decision queue without actuators. | 5, 6, 7, 8 |
| 10 | Wire governed actuation behind grants | Add claim, dispatch, harvest, review-route, preflight, PR-update, and merge-gate actions behind G-grants; keep R-reserved blocked. | 2, 6, 7, 9 |
| 11 | Add Orchestrator evals and trace review | Create eval scenarios for stalled workers, path collisions, missing review, red CI, R-reserved requests, and conveyor pickup. | 3, 5, 10 |
| 12 | CEO-mode / strangeLoop integration design | Define how CEO-mode uses the cockpit and how `strangeLoop` contributes independent review without privileged authority. | 8, 9, 11 |

Suggested dependency path:

```text
1 -> 2 -> 3 -> 4
1 -> 5 -> 6 -> 7
2 + 5 -> 8
5 + 6 + 7 + 8 -> 9
2 + 6 + 7 + 9 -> 10
3 + 5 + 10 -> 11
8 + 9 + 11 -> 12
```

## Acceptance Criteria

For this design:

- The document defines the Orchestrator role as a lifecycle owner rather than
  a code-producing worker.
- It covers intake, territory map, dispatch, progress/stall watch, harvest,
  independent review, gate/merge, conveyor next lane, checkpointing, and
  Operator decision surfacing.
- It distinguishes autonomous decisions from Operator escalation.
- It defines G1-G5/R-reserved at the contract level and records the missing
  ADR/substrate-detail gap while grounding cadence and grant snapshots in the
  root resume-state checkpoints.
- It describes governed worker roles, model/effort routing implications,
  contained vs non-contained seats, and harvest mechanics.
- It grounds deterministic knowledge loading in the controller-bootstrap
  overlay, playbooks, proposed skill pointers, company brain, and root
  resume-state checkpoints.
- It defines cadence, cockpit/CEO-mode composition, risks, and a sliced
  ce-ops epic with dependencies.

For future implementation:

- No Orchestrator action should execute without a visible record naming the
  grant, target, predicates, and result.
- No worker should receive broader mount, egress, credential, or path authority
  than its role and dispatch envelope require.
- No merge should happen without independent review, green validation, declared
  work class, ratification, and applicable grant predicates.
- No R-reserved action should proceed without an Operator authority record.

## References

- In-tree: `docs/design/controller-bootstrap-ssot.json`
- In-tree: `docs/design/controller-bootstrap-injection.md`
- In-tree: `playbooks/controller/workflow.ce.yml`
- In-tree: `playbooks/controller/briefs/dispatch.md`
- In-tree: `playbooks/controller/briefs/merge-gate.md`
- In-tree: `specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`
- In-tree: `.claude/agents/README.md`
- Read-only root checkout context:
  `/home/ce-dev-1/creator-engine/.ce/state/research/RESUME_STATE_CE_DEV2_*`
- OpenAI Agents SDK docs: <https://developers.openai.com/api/docs/guides/agents>
- Anthropic, "How we built our multi-agent research system" (2025-06-13):
  <https://www.anthropic.com/engineering/multi-agent-research-system>
- LangChain multi-agent docs:
  <https://docs.langchain.com/oss/python/langchain/multi-agent>
- Microsoft AutoGen docs: <https://microsoft.github.io/autogen/stable/>
- OrchVis paper (2025-10): <https://arxiv.org/html/2510.24937v1>
