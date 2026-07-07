# CE-491 Option A: Merge-Time Brain Append Intent Materialization

## Status

Design-only proposal. This document does not grant authority, add schema files,
or implement a materializer.

## Goal

Option A replaces direct PR edits to `.ce/brain/assertions.yaml` with data-only
append intents that are materialized after the PR lands. The design must preserve
the append ledger's hash-chain semantics while removing stale-tail pressure from
normal PR authoring.

The slice-1 stale-tail gate in
`docs/design/ce-491-ledger-append-serialization-slice1.md` remains the backstop
for legacy direct ledger edits. Option A is the follow-on design for the mediated
append target deferred by that slice.

## Constraints

- The forge merge queue authors the merge commit. Ledger materialization is
  therefore a post-merge action by a separate actor.
- The merge gate is the policy singleton. This design must not create a second
  gate-authority holder.
- Intent-carrying PRs must not edit `.ce/brain/assertions.yaml` directly.
- Failed, malformed, or unprovable materialization must be visible and
  fail-closed. The actor must never silently drop an intent.
- Arming any direct write authority to `main` is an Operator decision. This
  design describes the authority boundary; it does not grant it.

## Owning Actor Recommendation

Recommendation: the merge-gate queue daemon owns post-merge intent
materialization, under a narrow Operator-armed direct-commit authority.

The reason is ownership locality. The daemon already observes merge admission,
merge completion, queue order, and closeout state. Materialization is not a new
policy decision; it is deterministic closeout work for a PR that the singleton
gate already admitted. Keeping the action under the existing singleton avoids a
second authority that could disagree with the gate.

| Candidate | Strengths | Risks | Verdict |
| --- | --- | --- | --- |
| Merge-gate queue daemon | Already observes queue order and merge completion; can serialize materialization after each landed PR; keeps policy under the existing singleton; can emit closeout evidence in the same place as gate evidence. | Requires a new, narrow direct-commit-to-main authority; daemon crashes can delay closeout; operator arming must be explicit and auditable. | Recommended. Best fit if authority is tightly bounded and fail-closed. |
| Integrator | Natural owner for merge mechanics and post-merge repair patterns; familiar with branch and git operations. | Becomes a second practical gate holder if it can decide or perform ledger closeout independently; less direct visibility into queue daemon state; risks splitting policy from materialization. | Do not choose. Keep merge mechanics and policy singleton separate from deterministic ledger closeout. |
| Merge-group CI job | CI is already required and reproducible; no long-running daemon lifecycle; natural place to validate intents before merge. | Cannot materialize after the forge-authored merge commit without a separate write credential; CI retry semantics are awkward for direct main writes; would create another authority surface adjacent to the gate. | Use CI for validation only, not post-merge mutation. |

## Authority Contract

The recommended actor needs one new authority, if and only if the Operator arms
it: create a materialization commit directly on `main` after a merge queue merge
has completed.

Bounds for that authority:

- It may run only for a merged PR whose merge commit includes one or more valid
  intent files under `.ce/brain/append-intents/`.
- It may create commits whose file changes are limited to:
  `.ce/brain/assertions.yaml` and the consumed intent files under
  `.ce/brain/append-intents/`.
- It must remove each successfully consumed intent file in the same commit that
  appends its ledger record.
- It must not edit implementation code, schemas, changelog fragments, manifests,
  workflows, or any path outside the bounded ledger and consumed-intent set.
- It must push with a compare-and-swap expectation: parent equals the current
  `main` tip observed immediately before materialization. If `main` moves, the
  actor refetches and revalidates before trying again.
- It must verify after push that `main` contains the intended materialization
  commit and that the consumed intent paths are absent.
- It must emit deterministic evidence for every success, refusal, retry, and
  quarantine.

Arming this authority is BLOCKING-FOR-IMPLEMENTATION and requires an Operator
ruling. Until armed, the materializer can run only in dry-run or advisory mode.

## Intent Lifecycle

### Path

Intent files live at:

```text
.ce/brain/append-intents/<branch-slug>.yaml
```

If one branch needs multiple appends, the preferred form is a single file with
multiple ordered entries rather than multiple files. That keeps PR-to-intent
mapping deterministic for validators. A future extension may allow
`.ce/brain/append-intents/<branch-slug>/<intent-id>.yaml`, but that is outside
this design.

### Inline Schema Sketch

This is a documentation sketch, not a tracked schema file:

```yaml
version: 1
branch_slug: ce-123-example
pr_number: 123
intent_id: ce-123-example:brain-append:001
authoring:
  head_sha: "<40-hex-pr-head-sha>"
  authored_at: "2026-07-07T00:00:00Z"
append:
  subject: "governance.example"
  predicate: "records"
  object: "A concise assertion payload."
  rationale: "Why this assertion belongs in the brain ledger."
  evidence:
    kind: "pr"
    uri: "https://example.invalid/repo/pull/123"
    sha256: "<64-hex-content-or-evidence-digest>"
  tags:
    - "brain"
```

Validation rules:

- `version` must be a known integer.
- `branch_slug` must equal the PR branch slug and the filename stem.
- `intent_id` must be stable and unique within the intent file.
- Intent content is data-only. It must not carry a precomputed `content_hash` or
  `prev_hash`; those are assigned at materialization against the live tail.
- Evidence digests must be syntactically valid and deterministic.
- The PR must not change `.ce/brain/assertions.yaml` when it carries an append
  intent, unless it is explicitly using the legacy direct-ledger path and passes
  the slice-1 stale-tail gate.

### State Machine

1. Authored: the PR adds `.ce/brain/append-intents/<branch-slug>.yaml`.
2. PR validated: CI validates path, syntax, data-only shape, branch slug, and
   evidence digest shape. CI does not assign ledger hashes.
3. Landed pending materialization: the merge queue lands the PR. The intent file
   is now present on `main`; closeout is not complete.
4. Materializing: the owning actor takes a lease, refetches `main`, reads the
   live ledger tail, validates the intent again, appends one or more ledger
   records, and removes the consumed intent file.
5. Materialized: the actor pushes a direct materialization commit to `main` that
   contains the ledger append and consumed-intent removal.
6. Closed out: evidence is emitted to the PR comment stream and durable daemon
   log. The landed tree has no unconsumed intent from that merged PR.

Invariant after successful closeout:

```text
main contains zero unconsumed .ce/brain/append-intents/<branch-slug>.yaml files
for PRs that have completed merge closeout.
```

A validator can enforce this by listing intent files on `main`, resolving their
`branch_slug`/`pr_number`, and checking whether the corresponding PR is merged
and past closeout. If yes, the file is a hard failure.

### Consume-And-Remove Semantics

Successful materialization consumes and removes the intent file. The intent is
retained as evidence through:

- the removed file's content in git history at the merge commit;
- `intent_sha256` and `intent_path` copied into the appended ledger record;
- the materialization commit SHA;
- the PR closeout comment;
- the daemon's append-only materialization log.

Retaining consumed intent files in the live tree is rejected because it leaves
ambiguous state: validators cannot tell whether a visible intent is pending,
already materialized, or accidentally skipped.

## Materialization Algorithm

For each merged PR that carries an intent:

1. Acquire the materialization lease for `brain-append:<merge-commit-sha>`.
2. Fetch `main` and resolve the live tip.
3. Verify the merge commit contains the expected intent file and that the file's
   canonical SHA-256 matches the value observed at discovery.
4. Re-validate the intent schema and data-only contract.
5. Load `.ce/brain/assertions.yaml` from the live tip and prove the current tail.
6. Build new ledger record(s) with `prev_hash` equal to the live tail and with
   mediation fields populated from the intent and merge metadata.
7. Write a tree that appends the records and removes the consumed intent file.
8. Commit with parent equal to the live tip.
9. Push with a ref expectation that `main` still equals that parent.
10. Re-read `main` and verify the materialization commit, tail hash, and
    consumed-intent removal.
11. Emit deterministic evidence.

If multiple landed PRs are pending, the actor processes them in observed merge
order. If it discovers a direct ledger edit on `main` between pending intents,
it must re-read the tail and continue only if the tail is provable.

## Failure And Crash Model

Materialization is idempotent by key:

```text
materialization_key = sha256(merge_commit_sha + "\n" + intent_path + "\n" + intent_sha256 + "\n")
```

Resume rules:

- Crash before commit creation: no main mutation exists; reacquire the lease and
  repeat from fetch.
- Crash after local commit before push: discard local commit, refetch `main`,
  and rebuild from the live tail.
- Push rejected because `main` moved: refetch, revalidate the intent, prove the
  new tail, and retry if the movement is explainable.
- Crash after push before evidence: detect the materialization commit on `main`
  by `materialization_key`, `intent_sha256`, and consumed-intent absence; then
  emit the missing evidence without appending again.
- Duplicate resume after success: no-op if the ledger contains exactly one
  record for the intent and the intent file is absent.

Unprovable live tail:

- If the actor cannot parse the live ledger, cannot identify the current
  `content_hash`, or sees an unexpected chain break, it must stop before any
  write.
- Surfaced state: `HELD` with reason `brain_ledger_tail_unprovable`.
- Operator-facing text should align with the #882 stale-tail gate vocabulary:
  "current ledger tail could not be proven" and "refused before materialization."

Malformed intent after PR CI:

- The actor must not append, remove, or rewrite the malformed intent on `main`.
- The actor writes an out-of-band quarantine artifact under its runtime evidence
  store, for example:
  `.ce/state/brain-intent-quarantine/<materialization-key>.json`.
- The artifact records the intent path, intent SHA-256, merge commit, validation
  error, actor version, and timestamp.
- Surfaced state: `HELD` with reason `brain_intent_materialization_failed`.
- The PR receives a closeout comment naming the held reason and quarantine
  artifact digest.
- Repair requires a follow-up PR or an Operator-approved manual recovery. The
  original intent is never silently dropped.

Partially materialized state:

- A state with ledger record appended but intent file still present is invalid.
  Resume must either prove that no materialization commit reached `main`, or
  hold with reason `brain_intent_partial_materialization`.
- A state with intent file removed but no matching ledger record is invalid and
  must hold with the same reason. The actor must not guess at repair.

## Evidence Contract

Every successful materialization creates evidence in three places.

Ledger record fields:

```yaml
mediation:
  mode: "merge_time_intent"
  intent_path: ".ce/brain/append-intents/<branch-slug>.yaml"
  intent_sha256: "<64-hex>"
  merge_commit_sha: "<40-hex>"
  materialization_commit_sha: "<40-hex>"
  materialization_key: "<64-hex>"
  actor: "merge-gate-queue-daemon"
```

PR closeout comment:

```text
Brain append intent materialized.
intent: .ce/brain/append-intents/<branch-slug>.yaml
intent_sha256: <64-hex>
merge_commit: <40-hex>
materialization_commit: <40-hex>
ledger_tail: <64-hex>
```

Daemon log:

- Append-only JSON Lines.
- One event per discovery, validation, retry, hold, success, and evidence-emitted
  step.
- Each event includes `materialization_key`, `intent_sha256`,
  `merge_commit_sha`, `main_parent_sha`, result status, and a canonical event
  SHA-256.

The ledger record is the durable repository-local evidence. The PR comment is
operator-facing evidence. The daemon log is execution evidence for audits and
crash recovery.

## Interaction With The #882 Stale-Tail Gate

Intent-carrying PRs no longer edit `.ce/brain/assertions.yaml` directly. The
#882 stale-tail gate therefore should not serialize normal intent PRs behind a
zero-drift requirement for the live ledger tail. They can merge while other
intent PRs are pending because no PR carries precomputed `prev_hash` or
`content_hash` values.

The #882 gate remains unchanged for legacy PRs that directly change
`.ce/brain/assertions.yaml`. Those PRs still carry pre-chained ledger bytes and
must be refused when the live base tail moved after their PR base.

Additional validation for intent PRs should be shape-focused:

- intent file path and branch slug match;
- intent is data-only;
- evidence digest fields are deterministic;
- direct `.ce/brain/assertions.yaml` edits are absent.

The materializer, not PR CI, assigns the live `prev_hash` and `content_hash`.

## Scheduled Drill And Test Plan

Unit tests:

- Validate intent schema success and failure cases.
- Verify branch slug must match file stem and `branch_slug`.
- Verify intent canonicalization produces stable `intent_sha256`.
- Verify direct `.ce/brain/assertions.yaml` edits remain routed to the #882
  stale-tail gate.
- Verify materialization record generation from a live tail.
- Verify consumed-intent removal and ledger append occur in one tree diff.
- Verify duplicate resume after success is a no-op.

Integration tests:

- Create two PR-like branches with append intents, land them in order, and prove
  materialization appends both records against successive live tails.
- Simulate `main` moving between fetch and push; verify compare-and-swap retry.
- Simulate malformed intent on `main`; verify hold, quarantine evidence, and no
  ledger mutation.
- Simulate crash at each stage: before commit, after local commit, after push
  before evidence, and during evidence emission.
- Simulate a broken live ledger tail; verify `HELD` /
  `brain_ledger_tail_unprovable` and no write.

Scheduled drill:

- Run a monthly dry-run drill in a disposable repository or isolated branch that
  exercises merge, materialization, evidence emission, and idempotent resume.
- Run a quarterly failure drill covering malformed intent, tail-unprovable hold,
  and crash-after-push evidence recovery.
- Drill success criteria: no unconsumed intents after successful closeout; no
  direct ledger edit in intent PRs; one ledger record per intent; evidence
  present in ledger, PR comment, and daemon log; failure cases produce explicit
  `HELD` state and no silent drops.

## Open Operator Questions

1. BLOCKING-FOR-IMPLEMENTATION: Should the merge-gate queue daemon be armed with
   the narrow direct-commit-to-main authority described above?
   Recommendation: yes, because it preserves the singleton gate model and keeps
   materialization in deterministic closeout.

2. BLOCKING-FOR-IMPLEMENTATION: Which credential and branch-protection exception
   should carry the materialization authority?
   Options: a dedicated app credential with path-scoped policy, or an existing
   gate credential with an additional materialization-only mode.
   Recommendation: use a dedicated app credential whose policy refuses any diff
   outside `.ce/brain/assertions.yaml` and consumed intent files.

3. BLOCKING-FOR-IMPLEMENTATION: Should quarantine artifacts remain out-of-band
   in runtime evidence, or should a later design add a tracked quarantine area?
   Recommendation: keep quarantine out-of-band for this authority. Tracked
   quarantine would require broader direct-write bounds and should be a separate
   Operator-approved design.

