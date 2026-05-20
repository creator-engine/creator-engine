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

PCO introduces four coordination primitives. Slice 0 introduces the
**schema and protocol** for all four; runtime mechanics arrive in
later slices.

| Primitive | Purpose | Slice 0 substance |
|---|---|---|
| **Claim** | "Controller X is currently driving lane L on worktree W under envelope E." | Tracked record shape; validator; protocol §h. |
| **Heartbeat** | "Claim is still live as of timestamp T, sequence N." | Tracked record shape; validator; protocol §i. |
| **Lane** | The coordination unit that claims and heartbeats reference. | `lane_id` pattern in schema; protocol §g. |
| **Event log** | Append-only record of `claim_created`, `claim_released`, `claim_lapsed`, `heartbeat_emitted`, `lane_handoff_announced`, `lane_handoff_received`. | Tracked record shape; validator; protocol §j, §n. |

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

1. **Slice 0 — Active-Work Ledger (this slice).** Tracked record
   schema + prose protocol + architecture doc + validator skeleton.
   Records and validates one record at a time. Does **not** enforce
   multi-controller execution.
2. **Slice 1 — Conflict Validator.** Cross-record overlap detection:
   worktree-path collision, lane uniqueness per controller,
   heartbeat monotonicity per claim, event-id uniqueness within the
   `(controller, lane, day)` scope.
3. **Slice 2 — Worktree Allocator.** Short-lived worktree leases
   that line up with ledger claims; resolves contention before a
   claim is written.
4. **Slice 3 — Pane Registry.** Visible-pane identity records — which
   Architect/Implementer pane is bound to which claim, on which host.
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
* live conflict detection (no cross-record checks; that is Slice 1);
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
   clone and observe that the new `active_work_ledger_schema` check
   is registered and passes on the worktree.
5. Trace each Slice 0 claim back to existing canonical doctrine
   (one-driver-per-worktree, controller boundary policy, Feature 001
   ratification) and confirm that PCO layers onto, rather than
   replaces, that doctrine.
