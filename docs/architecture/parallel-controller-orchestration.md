# Creator Engine Parallel Controller Orchestration (PCO)

**Status**: Reference. Slice 0 substrate authored under PCO Slice 0
(Active-Work Ledger).

**Source-of-truth relationship**: REFERENCE. This document defers to
the Feature 001 governance substrate, the Feature 002 operating
model, [`./agentic-sdlc-operating-model.md`](./agentic-sdlc-operating-model.md),
[`./agent-interaction-model.md`](./agent-interaction-model.md), and
[`./parallel-agent-development-model.md`](./parallel-agent-development-model.md)
for the underlying SDLC mechanics, actor patterns, and the
one-driver-per-worktree rule. It is authoritative for the
multi-Controller coordination substrate within Feature 005's scope,
and it is the architectural companion to the prose protocol at
[`../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md`](../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md).

## a. Status and source-of-truth

| Upstream source of truth | Role |
|---|---|
| Feature 001 governance substrate | Author/approver separation; privileged-class enumeration; ratification flow. |
| Feature 002 operating model | Assignment-Envelope contract; verifies-not-ratifies; authority-conflict halt path. |
| [`./parallel-agent-development-model.md`](./parallel-agent-development-model.md) | One-driver-per-worktree rule; the parallel-pair shape. |
| [`./agent-interaction-model.md`](./agent-interaction-model.md) | Actor-to-actor visible-pane patterns. |
| [`./agentic-sdlc-operating-model.md`](./agentic-sdlc-operating-model.md) | Operating-model state machine. |
| [`../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md`](../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md) | Prose protocol companion (Slice 0). |
| [`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md) | Controller / Implementer boundary policy. |
| `schemas/active-work-ledger.schema.yaml` | Tracked machine-readable record contract. |

## b. Problem statement

The parallel-agent development model establishes that *two Claude Code
sessions MUST NOT write concurrently to the same physical worktree*
and that *two Hermes+Claude pairs MAY work on different features in
parallel provided each pair has its own worktree*. That rule is the
floor. It is necessary but not sufficient once **more than one
Source-ratified Controller** is in play — for example, when a Hermes
pane and a second Nefarious pane both hold ratified envelopes and
both intend to drive Architect/Implementer pairs simultaneously.

The unsolved coordination question is:

> Given multiple Source-ratified Controllers, **which Controller is
> currently driving which lane of work**, and how does a Controller
> verify that fact before it launches a parallel pane?

This document specifies the architectural substrate that answers that
question. The substrate is **Parallel Controller Orchestration
(PCO)**. Slice 0 introduces the schema and protocol primitives;
later slices add validators, allocators, and integration tooling.

## c. Canonical doctrine the model preserves

PCO is layered onto, not in place of, existing canonical doctrine.
The following invariants remain in force unchanged:

1. **Hermes / Nefarious as Controller.** A Controller is a *verifier*,
   not an author. The Controller relays envelopes, archives
   transcripts, hashes prompts/transcripts, runs preflight and scope
   audits, and does not author tracked-file content under an envelope
   it is verifying. PCO does not promote the Controller to an
   author.
2. **Visible external Architect / Implementer panes, not Claude Code
   internal subagents.** Parallel work is performed in **visible**
   external panes — separate Claude Code sessions, each its own
   process, each with its own transcript — under
   one-driver-per-worktree. PCO does not introduce Claude Code
   subagent orchestration.
3. **One driver per physical worktree.** Every claim names exactly
   one `worktree_path` and exactly one driving `controller_id`. Two
   live (non-stale) claims for the same `worktree_path` under
   different `controller_id` values is a substrate-level conflict
   that later slices reject.
4. **Source-ratified privileged gates.** PCO does not relax Feature
   001's privileged-class enumeration or the Source ratification
   flow. Every claim still operates under a ratified envelope; the
   ledger does not grant authority.
5. **Serialized canonical-branch integration.** Multi-lane authorship
   does not become multi-lane *merge*. Canonical-branch integration
   remains serialized and Source-ratified; later slices add an
   explicit integration queue.
6. **Fan-in verification does not trust lane self-report.** When
   multi-lane authorship lands, the fan-in verification step
   (`pco-fanin`, Slice 5) reconstructs the integrated state from
   tracked artifacts and validator output, not from each lane's
   own claim of completion.

## d. Coordination primitives

PCO introduces five coordination primitives. Slice 0 introduces the
**schema and protocol** for the first four; Slice 0.5 adds the fifth
(Completion Report). Runtime mechanics arrive in later slices.

| Primitive | Purpose | Slice substance |
|---|---|---|
| **Claim** | "Controller X is currently driving lane L on worktree W under envelope E." | Slice 0: tracked record shape; validator; ledger protocol §h. |
| **Heartbeat** | "Claim is still live as of timestamp T, sequence N." | Slice 0: tracked record shape; validator; ledger protocol §i. |
| **Lane** | The coordination unit that claims and heartbeats reference. | Slice 0: `lane_id` pattern in schema; ledger protocol §g. |
| **Event log** | Append-only record of `claim_created`, `claim_released`, `claim_lapsed`, `heartbeat_emitted`, `lane_handoff_announced`, `lane_handoff_received`. Slice 0.5 adds `gate_opened`, `gate_closed`, `completion_report_emitted`, `gate_blocked`. | Slice 0 + 0.5 additive: tracked record shape; validator; ledger protocol §j, §n, §n.1. |
| **Completion Report** | Deterministic return packet for every Source-ratified gate. Binds envelope+SHA to outcome, evidence, and the next ratifiable prompt pointer. | Slice 0.5: tracked schema (`schemas/completion-report.schema.yaml`); prose protocol [`../operations/COMPLETION_REPORT_PROTOCOL.md`](../operations/COMPLETION_REPORT_PROTOCOL.md); per-class templates; CR-001/CR-002/CR-003 validators. |

The runtime directory shape (`.hermes/active-work-ledger/`), the
atomic-write rule (temp + fsync + rename), the advisory-lock rule
(`flock(2)` on `locks/<lane-id>.lock`), and the pre-launch
read/validate discipline are documented in
[`../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md`](../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md)
§§e, l, m, o.

## e. Slice plan

PCO is delivered in slices. Each slice keeps the
substrate-before-automation discipline: protocol and validator first,
runtime tooling after.

1. **Slice 0 — Active-Work Ledger.** Tracked record schema + prose
   protocol + architecture doc + validator skeleton. Records and
   validates one record at a time. Does **not** enforce
   multi-controller execution.
1.5. **Slice 0.5 — Completion Report Substrate.** Tracked completion-
   report schema + prose protocol + per-class templates + well-formed
   and malformed examples + CR-001 / CR-002 / CR-003 validator checks.
   Additively extends the Slice 0 schema with four new event kinds.
   Records and validates only; the Hermes final-answer hook is
   reserved for the follow-on Slice 0.5R and ratified separately.
2. **Slice 1/2 — Conflict / Pre-Launch Validator.** Cross-record
   overlap detection: worktree-path collision, live lane uniqueness
   per controller, heartbeat claim-reference resolution, event
   subject-claim-reference resolution, heartbeat monotonicity per
   claim where timestamps are parseable, and event-id uniqueness
   within the `(controller, lane, day)` scope. This is validator-only:
   it refuses unsafe pre-launch state but does not allocate worktrees
   or launch panes.
2.5. **Slice 2A — Worktree Lease Substrate.** Tracked Worktree Lease
   record schema (`schemas/worktree-lease.schema.yaml`) + prose
   protocol ([`../operations/WORKTREE_LEASE_PROTOCOL.md`](../operations/WORKTREE_LEASE_PROTOCOL.md))
   + well-formed and malformed examples + new
   `worktree_lease_schema` validator check (`PCO-020`) +
   additive predicates in `active_work_ledger_conflicts`:
   `claim_requires_live_lease` (`PCO-021`),
   `worktree_lease_conflict` (`PCO-022`), and
   `worktree_lease_invalid_record` (`PCO-023`). The lease-aware
   predicates are gated on the discovery of at least one valid
   lease record in the scanned tree, so trees with zero lease
   records preserve Slice 1/2 behavior unchanged. Slice 2A is
   substrate-only: it does NOT allocate worktrees, does NOT
   mutate `git worktree` state, does NOT ship a `pco-allocate` /
   `pco-release` CLI, does NOT introduce a Hermes runtime hook,
   does NOT re-enable `pco-completion-gate`, and does NOT solve
   cryptographic controller-identity binding. Runtime allocation
   is reserved for Slice 2R; identity hardening is reserved for a
   separately ratified follow-on workstream.
3. **Slice 2R — Worktree Allocator Runtime.** Ships `pco-allocate` /
   `pco-release` CLI, advisory lane lock, atomic `git worktree add` +
   lease + claim + event flow, claim-writes-only-under-held-lease
   enforcement, callable pane-launch guard, and root-checkout
   refusal. Slice 2R is the runtime sibling of Slice 2A. Prose
   contract:
   [`../operations/WORKTREE_ALLOCATOR_PROTOCOL.md`](../operations/WORKTREE_ALLOCATOR_PROTOCOL.md).
   **Slice 2R does NOT ship a Hermes runtime hook, does NOT
   containerize the Controller, does NOT launch visible tmux panes,
   does NOT introduce a pane registry, does NOT mutate GitHub settings
   or branch configuration beyond the new worktree branch, and does
   NOT expand Phase 1 / Phase 2 autonomy.**
3.5. **Slice 2I — Worker Isolation Runtime (substrate authored;
   runtime deferred).** Sibling/bridge slice authored between the
   Slice 2.5 + 2R authoring gate and the Slice 2.5 + 2R
   implementation gate. Introduces the worker-container substrate
   that sits beneath the visible tmux pane: a tracked
   worker-container policy record (role: `architect_research` |
   `implementer` | `verification`), a tracked container-instance
   record, a mount manifest, a secret-grant manifest without
   secret values, a network (egress allowlist) policy record, an
   artifact collection manifest, and termination /
   garbage-collection event records. Declares the kernel/syscall
   verb set (`allocate_worker`, `mount_workspace`,
   `grant_path_capability`, `inject_secret`, `set_network_policy`,
   `run_command`, `collect_artifacts`, `terminate_worker`,
   `garbage_collect_worker`) and the substrate-level refusal
   predicates `PCO-040` through `PCO-045`. Ratifies a default-deny
   safety floor (read-only mounts by default; no host home mount;
   no host SSH/GitHub/model-provider credentials by default; no
   container engine socket inside a worker container; role-specific
   egress; redaction + revocation expectations for secrets) and
   the rule that the Slice 2.5 controller-key private key is
   never injected into a worker container. Container engine,
   image baseline, credential broker, egress enforcement
   primitive, image separation by role, mount-grant authority,
   and a per-container ephemeral controller-key amendment to
   OSD-1 are recorded as Open Source Decisions. Slice 2I splits
   into **Slice 2I-S** (substrate; contract authoring) and
   **Slice 2I-R** (runtime; engine wiring, allocator extension
   between PCO-027 steps 5 and 6, credential broker, egress
   primitive — separately ratified, deferred). Slice 2I-S does
   NOT amend `PCO-024` through `PCO-032`; does NOT containerize
   the Controller; does NOT build, pull, run, or inspect any
   container image; and does NOT expand Phase 1 / Phase 2
   autonomy. Spec amendment lives at
   [`../../specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`](../../specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md).
4. **Slice 3 — Pane Registry.** Visible-pane identity records — which
   Architect/Implementer pane is bound to which claim, on which host.
   Pane identity binds to a container-instance id (when present) per
   the Slice 2I-S substrate; Slice 3 should be authored against
   Slice 2I-S to avoid a v2 migration.
5. **Slice 4 — Side-Effect Ledger.** Tracks externally observable
   side effects per lane (CI runs, deploys, GitHub state mutations)
   as structured input for fan-in.
6. **Slice 5 — `pco-fanin`.** Integration verification under
   multi-lane authorship; reconstructs the integrated state from
   tracked artifacts and validator output, not from lane self-report.
7. **Slice 6 — Integration Queue.** Serialized canonical-branch
   landing order across lanes; Source-ratified.

**Slice 0 boundary, restated normatively**: Slice 0 records and
validates Active-Work Ledger entries; it does **not** yet enforce
multi-controller execution, does **not** yet detect cross-lane
semantic conflicts, and does **not** yet allocate worktrees.
Enforcement is reserved for later PCO slices.

## f. Non-goals (Slice 0)

Slice 0 explicitly does NOT introduce:

* runtime enforcement of any kind (no multi-controller writing
  trials, no live coordination tooling);
* live conflict detection beyond the read-only `active_work_ledger_conflicts`
  pre-launch checks (semantic conflict analysis and runtime coordination remain
  later-slice concerns);
* automatic worktree allocation (that is Slice 2);
* model, tool, CLI, account, runner, or QA-harness bindings (those
  remain deployment-time overlay decisions);
* replacement of Assignment Envelopes or handoffs as substantive
  authority;
* replacement of Source ratification.

## g. Acceptance posture

A fresh-clone reviewer must be able to:

1. Read this document and identify the seven PCO slices, the Slice 0
   boundary, and the Slice 0 non-goals.
2. Read
   [`../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md`](../operations/ACTIVE_WORK_LEDGER_PROTOCOL.md)
   and reconstruct the runtime directory shape, the record fields,
   the lease semantics, the atomic-write rule, the advisory-lock
   rule, and the pre-launch read/validate discipline.
3. Read `schemas/active-work-ledger.schema.yaml` and verify that the
   schema mirrors the prose contract.
4. Run the validator (`creator_engine_validator check`) from a fresh
   clone and observe that both `active_work_ledger_schema` and
   `active_work_ledger_conflicts` are registered; use
   `creator_engine_validator scan-active-work-ledger-conflicts <path>`
   for the focused pre-launch layer.
5. Trace each Slice 0 claim back to existing canonical doctrine
   (one-driver-per-worktree, controller boundary policy, Feature 001
   ratification) and confirm that PCO layers onto, rather than
   replaces, that doctrine.

## h. Slice 2A substrate boundary statement

**Slice 2A records, validates, and refuses Worktree Lease state; it
does NOT yet allocate worktrees, does NOT mutate `git worktree`
state, does NOT ship a `pco-allocate` / `pco-release` CLI, does NOT
re-enable `pco-completion-gate`, and does NOT solve cryptographic
controller-identity binding. Runtime allocation is reserved for
Slice 2R. Identity hardening is reserved for a separately ratified
follow-on workstream.** This statement is normative and reproduced
verbatim in
[`../operations/WORKTREE_LEASE_PROTOCOL.md`](../operations/WORKTREE_LEASE_PROTOCOL.md)
and in
[`../../specs/005-pco-parallel-controller-orchestration/spec.md`](../../specs/005-pco-parallel-controller-orchestration/spec.md).

## j. Slice 2R runtime boundary statement (PCO-032)

**Slice 2R ships `pco-allocate` and `pco-release`, the advisory lane
lock, and claim-writes-only-under-held-lease enforcement. It does NOT
ship a Hermes runtime hook, does NOT containerize the Controller, does
NOT launch visible tmux panes, does NOT introduce a pane registry,
does NOT mutate GitHub settings or branch configuration beyond the new
worktree branch, and does NOT expand Phase 1 / Phase 2 autonomy. Each
`pco-allocate` and `pco-release` execution is a discrete, manually
invoked CLI call under a Source-ratified envelope; no autonomous
execution sequence is introduced.** The prose contract is at
[`../operations/WORKTREE_ALLOCATOR_PROTOCOL.md`](../operations/WORKTREE_ALLOCATOR_PROTOCOL.md)
§k.

## i. Slice 2I-R runtime boundary statement

**Slice 2I-R** is the runtime gate for the Worker Isolation Runtime.
It is separately ratified and deferred from the Slice 2I-S substrate
authoring gate. The Slice 2I-R spec (prose level only, no
implementation produced) is authored in §§l–r of
[`../../specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`](../../specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md).

The Slice 2I-R runtime mechanics extend two existing PCO entry points:

- **`pco-allocate` extension (PCO-027 step 5.b)**: after step 5
  (worktree add + lease + claim + `claim_created` event) and before
  the lane lock is released, Slice 2I-R conditionally selects the
  ratified worker-container policy, starts the container under that
  policy, mounts the worktree, applies the network egress policy,
  injects per-task scoped credentials, writes the container-instance
  record, and emits a `container_started` event — all under the same
  lane lock. The extension is conditional on the presence of at least
  one worker-container policy record in the scanned tree; trees
  without policy records preserve PCO-027 unchanged.

- **`pco-release` extension (PCO-028 step 3.b)**: before step 3
  (`git worktree remove`), Slice 2I-R conditionally terminates the
  paired container, records exit status, emits `container_stopped`,
  and revokes all claim-scoped credentials — under the same lane
  lock. `pco-release` MUST refuse `git worktree remove` if the
  paired container cannot be brought to a confirmed terminal state.
  The extension degrades gracefully for pre-Slice-2I-R claims with
  no container-instance record.

PCO-042 (`container_required_for_claim`) is the runtime-gate
predicate that enforces the pairing between live claims and running
container instances when a policy record is present. PCO-043
(`container_outlives_claim`) is the static-surface predicate that
backs the periodic sweeper that force-reaps orphaned container
instances. Both are declared in §g of the Slice 2I-S substrate and
refined to implementation-spec level in §m of the Slice 2I-R section.

The credential broker contract (§n of the runtime spec) specifies
that the broker is host-side, issues per-task fine-grained GitHub PATs
or App installation tokens bounded to one branch/repo/claim/TTL, and
revokes all tokens synchronously on release. The host operator's
`GH_TOKEN` MUST NOT enter any worker container. Secret values MUST
NOT appear in any tracked record.

The egress enforcement primitive (§o of the runtime spec) designates
Pasta as the Slice 2I-R default, with Slirp4netns with custom
configuration as an acceptable equivalent. Both primitives MUST
enforce the policy's `egress_allowlist` before the container's first
exec, surface violations as typed `egress_violation` events, and
record every non-default flag in the container-instance record.

**Slice 2I-R spec authoring gate non-goals** (normative, reproduced
from §q of the runtime spec): this gate produces no runtime code, no
container image, no container execution, no credential issuance, no
schema or validator implementation, no egress primitive
configuration, no Hermes-side mutation, and no autonomy expansion.
PCO-032 remains in force. This statement MUST be preserved in this
architecture doc when the Slice 2I-R implementation gate subsequently
lands.
