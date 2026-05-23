# Worktree Allocator Protocol

**Status**: PCO Slice 2R normative runtime protocol. Layered onto, and
subordinate to, the Feature 001 governance substrate, the Feature 002
operating model, the Slice 0 / Slice 1/2 Active-Work Ledger primitives,
and the Slice 2A Worktree Lease substrate.

## a. Purpose

Slice 2A defines the tracked Worktree Lease record schema and the
refusal predicates; it is substrate-only. Slice 2R ships the runtime
that acts on that substrate: the `pco-allocate` and `pco-release` CLI
commands. These commands convert the read/validate/refuse substrate into
a block-or-proceed runtime gate.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 governance substrate | Author/approver separation; ratification flow. |
| Feature 002 operating model | Assignment-Envelope contract; verifies-not-ratifies. |
| [`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md) | PCO slice plan; Slice 2R entry. |
| [`./WORKTREE_LEASE_PROTOCOL.md`](./WORKTREE_LEASE_PROTOCOL.md) | Slice 2A lease record schema and contract. |
| [`./ACTIVE_WORK_LEDGER_PROTOCOL.md`](./ACTIVE_WORK_LEDGER_PROTOCOL.md) | Active-Work Ledger claim/heartbeat/event shape. |
| [`./ROOT_WORKTREE_INVARIANT.md`](./ROOT_WORKTREE_INVARIANT.md) | Root-checkout invariant policy enforced by PCO-031. |
| `validators/creator_engine_validator/pco_allocator.py` | Slice 2R runtime implementation. |
| `schemas/worktree-lease.schema.yaml` | Tracked lease record contract. |
| `schemas/active-work-ledger.schema.yaml` | Tracked ledger record contract. |

## c. Scope of Slice 2R

Slice 2R is **runtime only**. It does NOT introduce new schemas,
validators, or tracked record shapes. It ships:

* `pco-allocate` CLI (`PCO-027`): lease + worktree + claim + event
  creation under an advisory lock with pre-flight conflict check;
* `pco-release` CLI (`PCO-028`): claim release + lease removal + event
  + worktree removal under an advisory lock;
* claim-writes-only-under-held-lease enforcement (`PCO-029`);
* callable pane-launch guard via `active_work_ledger_conflicts`
  (`PCO-030`);
* root-checkout refusal (`PCO-031`);
* Slice 2.5 + 2R boundary statement update (`PCO-032`).

Slice 2R does NOT:

* introduce new tracked schemas or validator check codes;
* push to remote, delete branches, open/close/merge PRs, or mutate
  GitHub settings;
* allocate panes or spawn visible tmux panes (that is Slice 3);
* introduce a Hermes runtime hook;
* containerize the Controller or introduce worker containers (that is
  Slice 2I-R);
* expand Phase 1 / Phase 2 autonomy.

## d. pco-allocate sequence (PCO-027)

All steps run under the lane's exclusive advisory lock on
`.hermes/active-work-ledger/locks/<lane-id>.lock`.

1. Refuse if `repo_root` is the main checkout (`is_root_checkout`
   detects `.git/` as a real directory — PCO-031).
2. Acquire exclusive `flock(LOCK_EX)` on the lane lock file.
3. Pre-flight: run `active_work_ledger_conflicts` guard; refuse the
   entire operation if any conflict exists (PCO-030).
4. Write the Worktree Lease record atomically to
   `.hermes/active-work-ledger/leases/<controller-id>/<lane-id>.yaml`
   using `<target>.tmp.<pid>.<nonce>` + rename (PCO-029: lease precedes
   claim; this is the structural ordering that enforces it).
5. Run `git worktree add -b <branch> <worktree-path>`. On failure,
   remove the lease (step 4) and raise `AllocationError`.
6. Write the Active-Work Ledger Claim record atomically to
   `.hermes/active-work-ledger/claims/<controller-id>/<lane-id>.yaml`.
7. Write a `claim_created` event record atomically under
   `.hermes/active-work-ledger/events/<YYYY>/<MM>/<DD>/`.
8. On any step-6/7 failure, remove all written records and run
   `git worktree remove` to roll back the worktree.

## e. pco-release sequence (PCO-028)

All steps run under the lane's exclusive advisory lock. Each step is
idempotent and tolerates partial prior completion.

1. Refuse if `repo_root` is the main checkout (PCO-031).
2. Acquire exclusive `flock(LOCK_EX)` on the lane lock file.
3. Mark claim released: set `released_at` and `release_reason` in
   `.hermes/active-work-ledger/claims/<controller-id>/<lane-id>.yaml`.
   Tolerate a missing claim file (mid-sequence recovery).
4. Remove the lease file at
   `.hermes/active-work-ledger/leases/<controller-id>/<lane-id>.yaml`.
   Tolerate an already-absent lease.
5. Append a `claim_released` event record under
   `.hermes/active-work-ledger/events/<YYYY>/<MM>/<DD>/`.
6. Run `git worktree remove --force <worktree-path>` (path read from
   the claim record). Tolerate an already-removed worktree.
   **Does NOT delete the branch. Does NOT push.**

## f. Advisory lock and atomic write discipline

`pco-allocate` and `pco-release` both:

1. Write records to a `.tmp.<pid>.<nonce>` sibling, then `rename(2)`.
2. Hold `flock(LOCK_EX)` on
   `.hermes/active-work-ledger/locks/<lane-id>.lock` around every
   read-modify-write sequence.

This matches the Slice 0 ledger atomic-write discipline documented in
[`./ACTIVE_WORK_LEDGER_PROTOCOL.md`](./ACTIVE_WORK_LEDGER_PROTOCOL.md)
§§l, m.

## g. Controller identity resolution (PCO-027, PCO-028)

The `--controller-id` CLI flag is optional. When omitted, Slice 2R
resolves the controller_id in this order:

1. `CREATOR_ENGINE_CONTROLLER_ID` environment variable.
2. `.hermes/controller-id` file under the repo root.
3. The most-recently-touched controller directory under
   `.hermes/active-work-ledger/claims/`.

If no convention yields a value, `pco-allocate` / `pco-release` exit
with an error and do not mutate any state.

## h. Root-checkout invariant (PCO-031)

`pco-allocate` and `pco-release` MUST NOT be executed from the root
(main) checkout. The allocator detects the root checkout by checking
whether `.git` under `repo_root` is a real directory (not a symlink
and not a file). In a secondary `git worktree add` worktree, `.git` is
a plain file; the root checkout has `.git/` as a real directory.

This enforcement mirrors the root-checkout invariant documented in
[`./ROOT_WORKTREE_INVARIANT.md`](./ROOT_WORKTREE_INVARIANT.md).

## i. Pane-launch guard (PCO-030)

The `active_work_ledger_conflicts` validator check (`run()` /
`validate_active_work_ledger_conflicts()`) is available as a direct
callable. Callers MUST invoke it and refuse pane launch when
`result.ok` is `False`. `pco-allocate` calls this guard (step 3 above)
before any filesystem mutation. The guard has no filesystem side
effects and does not spawn subprocesses.

## j. Claim writes only under held lease (PCO-029)

The Slice 2R sequence writes the Worktree Lease record (step 4) before
running `git worktree add` (step 5) and before writing the claim record
(step 6). This ordering ensures that, within the lane lock, the lease
is present at the moment the claim is written. The `pco-allocate`
implementation enforces this ordering structurally: the claim write is
inside a try-block that can only be reached after the lease write
completes.

## k. Slice 2R boundary statement (PCO-032)

**Slice 2R ships `pco-allocate` and `pco-release`, the advisory lane
lock, and claim-writes-only-under-held-lease enforcement. It does NOT
ship a Hermes runtime hook, does NOT containerize the Controller, does
NOT launch visible tmux panes, does NOT introduce a pane registry, does
NOT mutate GitHub settings or branch configuration beyond the new
worktree branch, and does NOT expand Phase 1 / Phase 2 autonomy. Each
`pco-allocate` and `pco-release` execution is a discrete, manually
invoked CLI call under a Source-ratified envelope; no autonomous
execution sequence is introduced.**

This statement is normative. It is reproduced in
[`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md)
and in
[`../product/ROADMAP.md`](../product/ROADMAP.md).

## l. Acceptance posture

A fresh-clone reviewer can verify the following from this document:

1. The pco-allocate sequence (§d) and the pco-release sequence (§e).
2. The advisory lock and atomic-write discipline (§f).
3. The controller identity resolution order (§g).
4. The root-checkout refusal rule (§h) and how it is detected.
5. The callable pane-launch guard and where it is invoked (§i).
6. The lease-precedes-claim ordering that implements PCO-029 (§j).
7. The Slice 2R boundary statement (§k) and what Slice 2R does NOT do.
