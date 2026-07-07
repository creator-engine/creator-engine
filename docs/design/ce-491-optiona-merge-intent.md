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
- The gate-daemon singleton is also the materializer execution assumption for
  this design. A multi-instance materializer is BLOCKING-FOR-IMPLEMENTATION and
  is left to Open Operator Question 4.
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

The current tracked schema describes one intent document per file. If one branch
needs multiple appends, it must use follow-up PRs or wait for a future schema and
path extension. A future extension may allow
`.ce/brain/append-intents/<branch-slug>/<intent-id>.yaml` or an ordered batch
envelope, but both are outside this design.

### Tracked Schema Reconciliation

Option A EXTENDS the existing tracked mediated-intent envelope from the latest
ce-488 remediation head, rather than superseding it. The authoritative files
are:

- `validators/creator_engine_validator/brain_append_intent.schema.yaml`
- `validators/creator_engine_validator/brain_append_worker.py`

The ce-488 schema is a tracked schema for the intent payload. It pins
`kind: brain-append-intent`, `schema_version: "1"`, and `intent_kind` routing
for `active_assertion_append`, `ce411_supersede_pair`, `decision_append`, and
`lesson_append`. Its payload blocks are mutually exclusive:
`active_assertion`, `supersede_pair`, `decision`, or `lesson`. The worker loads
that schema, rejects host/position-bearing fields such as `sequence`,
`prev_hash`, `content_hash`, `ledger_text`, `repo_root`, and `state_root`, then
uses `brain_runtime` to assign live ledger position fields from the current
tail.

Option A keeps those field meanings:

| Concern | ce-488 tracked contract | Option A reconciliation |
| --- | --- | --- |
| Kind discriminator | `kind` must equal `brain-append-intent`. | Same value. PR-carried intent files must validate against this discriminator before merge and again at materialization. |
| Schema version | `schema_version` is the string `"1"`, not an integer. | Same string form. Option A does not use the earlier integer `version` sketch. |
| Intent routing | `intent_kind` selects one of the supported operations. | Same routing. The materializer dispatches through the same operation vocabulary and refuses unknown values with `brain_append_intent_kind`. |
| Payload shape | Exactly one operation payload block is present. | Same mutually exclusive payload shape. `active_assertion_append` and `ce411_supersede_pair` materialize assertion records; `decision_append` and `lesson_append` materialize memory records. |
| PR binding | No `branch_slug`, `pr_number`, `head_sha`, `authored_at`, or `intent_id` fields are allowed because the schema has `additionalProperties: false`. | PR binding is derived outside the YAML payload: intent path stem supplies `branch_slug`, merge metadata supplies PR number/head/merge commit, and `materialization_key` binds the merge commit, intent path, and canonical intent SHA-256. Embedding PR-binding fields in the YAML would require a future schema revision and is outside this design. |

The PR-carried file content therefore remains a ce-488-style intent payload:

```yaml
kind: brain-append-intent
schema_version: "1"
intent_kind: active_assertion_append
active_assertion:
  assertion_id: brain-assertion-example-intent
  claim:
    subject: governance.example
    predicate: records
    object: concise assertion payload
  scope: creator-engine
  evidence_ref: docs/design/ce-491-optiona-merge-intent.md
  assertion_type: decision
  verification_method:
    type: static
    evidence_ref: docs/design/ce-491-optiona-merge-intent.md
```

Validation rules:

- `kind` must equal `brain-append-intent`.
- `schema_version` must equal the string `"1"`.
- `intent_kind` must route to exactly one payload block supported by the
  tracked schema.
- The filename stem must equal the PR branch slug; this is a path/PR binding
  rule, not an in-file schema field.
- Intent content is data-only. It must not carry a precomputed `content_hash` or
  `prev_hash`; those are assigned at materialization against the live tail.
- Evidence references must be local or opaque references accepted by the tracked
  schema and runtime; live URLs and host-specific identifiers remain outside the
  intent.
- The PR must not change `.ce/brain/assertions.yaml` when it carries an append
  intent. A hybrid PR with any `.ce/brain/append-intents/` file and any direct
  `.ce/brain/assertions.yaml` edit is refused by the
  `brain_append_intent_xor_direct_ledger` hard gate.

### State Machine

1. Authored: the PR adds `.ce/brain/append-intents/<branch-slug>.yaml`.
2. PR validated: CI validates path, syntax, data-only shape, branch slug, and
   evidence reference shape. CI does not assign ledger hashes.
3. Landed pending materialization: the merge queue lands the PR. The intent file
   is now present on `main`; closeout is not complete. Merge order is discovered
   from the merge-gate daemon's own accepted-merge stream and rechecked from git
   by walking `main` first-parent history in reverse chronological batches, then
   processing pending intent-bearing merge commits in first-parent order.
4. Materializing: the owning actor takes a lease for the brain-append ledger
   component, refetches `main`, reads the live ledger tail, validates the intent
   again, appends one or more ledger records, and removes the consumed intent
   file.
5. Materialized: the actor pushes a direct materialization commit to `main` that
   contains the ledger append and consumed-intent removal.
6. Closed out: evidence is emitted to the PR comment stream and durable daemon
   log. The landed tree has no unconsumed intent from that merged PR.

Invariant after successful closeout:

```text
main contains zero unconsumed .ce/brain/append-intents/<branch-slug>.yaml files
for PRs that have completed merge closeout.
```

A validator must enforce this by listing intent files on `main`, resolving the
branch slug from the path stem and the PR number from merge metadata, and
checking whether the corresponding PR is merged and past closeout. If yes, the
file is a hard failure.

### HELD State Cascade

`HELD` is scoped to the materialization component, not the whole merge gate. A
held brain append intent blocks later materialization for
`.ce/brain/assertions.yaml` only when later intents require the same live ledger
tail. Other gate work and other independent components may proceed.

A merged PR whose intent is `HELD` is not an immediate repository-wide hard
failure while it is inside the closeout window. The closeout window is 30
minutes from the time the merge commit first appears on `main` first-parent
history. During that window validators report advisory status:

```text
brain_append_intent_closeout: HELD advisory
reason: <held-reason>
materialization_key: <64-hex>
deadline_utc: <ISO-8601>
```

After the closeout window expires, the same condition becomes a hard gate failure
until the intent is materialized, repaired, or explicitly cleared by an
Operator-authorized recovery.

The daemon persists held state in its runtime state directory:

```text
.ce/state/brain-intent-materializer/held/<materialization-key>.json
```

On restart, the daemon reloads held records before scanning new work. If the
held reason is still true, it re-enters `HELD` without writing to `main`. If a
follow-up PR has repaired the condition, the daemon records the repair evidence,
revalidates the live tail, and resumes from the repaired `main`.

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

1. Acquire the materialization lease for the `brain-append` ledger component.
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

If multiple landed PRs are pending, the actor processes them in the first-parent
merge order described in the lifecycle. If it discovers a direct ledger edit on
`main` between pending intents, it must re-read the tail and continue only if the
tail is provable.

### Lease Contract

The materialization lease is stored out-of-band in the daemon runtime state:

```text
.ce/state/brain-intent-materializer/leases/brain-append.json
```

Lease fields are `component`, `holder`, `acquired_at_utc`, `expires_at_utc`,
`last_heartbeat_utc`, `main_tip_sha`, and `materialization_key`. The holder
heartbeats at least once every 60 seconds. The lease expires 15 minutes after
the last heartbeat.

The exclusion scope is the brain append ledger component
(`.ce/brain/assertions.yaml` plus consumed `.ce/brain/append-intents/` files),
not a single PR. This scope is required because all brain append intents share
one hash-chain tail.

This lease is sufficient only under the strict singleton gate-daemon topology
assumed by this design. If Operators choose a multi-instance materializer, this
local lease becomes diagnostic state only; correctness then requires an external
linearizable lock with the same `brain-append` exclusion scope.

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
  by the deterministic commit trailer `CE-Materialization-Key:
  <materialization-key>`, the ledger record's `materialization_key`, the
  `intent_sha256`, and consumed-intent absence; then emit the missing evidence
  without appending again.
- Duplicate resume after success: no-op if the ledger contains exactly one
  materialization set for the intent and the intent file is absent.

Unprovable live tail:

- If the actor cannot parse the live ledger, cannot identify the current
  `content_hash`, or sees an unexpected chain break, it must stop before any
  write.
- Surfaced state: `HELD` with reason `brain_ledger_tail_unprovable`.
- Operator-facing text should align with the #882 stale-tail gate vocabulary:
  "current ledger tail could not be proven" and "refused before materialization."
- Recovery path: a follow-up PR must repair the ledger chain or remove the
  blocking malformed state through normal governed review. Before the
  materializer authority is armed, manual recovery is allowed only by explicit
  Operator authorization recorded outside the repository and referenced by the
  daemon evidence; the daemon must not infer authorization from a chat transcript
  or local operator shell access.

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
- Follow-up PR semantics: the repairing PR either replaces the malformed intent
  with a valid intent at the same path or removes the intent with a documented
  superseding record. After that PR merges, the materializer revalidates the live
  tree and records the original `materialization_key`, the repair PR number, and
  the new merge commit in held-state evidence.

Partially materialized state:

- A state with ledger record appended but intent file still present is invalid.
  Resume must either prove that no materialization commit reached `main`, or
  hold with reason `brain_intent_partial_materialization`.
- A state with intent file removed but no matching ledger record is invalid and
  must hold with the same reason. The actor must not guess at repair.
- Recovery path: no automatic rewrite is allowed. A follow-up PR or explicit
  Operator recovery must restore one valid state: either the intent is present
  and pending, or the matching ledger record exists and the intent is absent.

## Evidence Contract

Every successful materialization creates evidence in four places.

### Materialized Ledger Record Schema

The materializer writes ordinary brain ledger records plus a deterministic
`mediation` block. The implementation must update the ledger schema before
arming this mode because the current `brain-assertion`, `brain-decision`, and
`brain-lesson` record schemas have `additionalProperties: false`.

For a materialized `active_assertion_append`, the record body fields and YAML
serialization order are:

```yaml
kind: "brain-assertion"
record_type: "brain_assertion"
schema_version: "1"
id: "<brain-assertion-id>"
statement: "<deterministic statement>"
type: "capability|convention|decision|gotcha"
verification_method: "<method-or-method-object>"
claim: {}
scope: "<scope-string-or-object>"
evidence_ref: "<local-or-opaque-reference>"
status: "active"
superseded_by: null
mediation:
  mode: "merge_time_intent"
  intent_path: ".ce/brain/append-intents/<branch-slug>.yaml"
  intent_sha256: "<64-hex>"
  intent_kind: "active_assertion_append"
  merge_commit_sha: "<40-hex>"
  pr_number: <integer>
  branch_slug: "<branch-slug>"
  materialization_key: "<64-hex>"
  materialization_record_index: 0
  materialization_record_count: 1
sequence: <integer>
prev_hash: "<64-hex>"
content_hash: "<64-hex>"
```

For a materialized `ce411_supersede_pair`, the materializer emits two
`brain-assertion` records in one commit. The first record has `status:
"superseded"` and `superseded_by` pointing to the replacement id. The second
record has `status: "active"` and `superseded_by: null`. Both carry the same
`materialization_key`; their mediation blocks set
`materialization_record_index` to `0` and `1`, and
`materialization_record_count` to `2`.

For a materialized `decision_append`, the record body fields and YAML
serialization order are:

```yaml
kind: "brain-decision"
record_type: "brain_decision"
schema_version: "1"
id: "<brain-decision-id>"
date: "YYYY-MM-DD"
scope: "<scope-string-or-object>"
statement: "<decision text>"
authority: "<authority>"
supersedes_ref: "<brain-decision-id-or-null>"
status: "active"
mediation:
  mode: "merge_time_intent"
  intent_path: ".ce/brain/append-intents/<branch-slug>.yaml"
  intent_sha256: "<64-hex>"
  intent_kind: "decision_append"
  merge_commit_sha: "<40-hex>"
  pr_number: <integer>
  branch_slug: "<branch-slug>"
  materialization_key: "<64-hex>"
  materialization_record_index: 0
  materialization_record_count: 1
sequence: <integer>
prev_hash: "<64-hex>"
content_hash: "<64-hex>"
```

For a materialized `lesson_append`, the record body fields and YAML
serialization order are:

```yaml
kind: "brain-lesson"
record_type: "brain_lesson"
schema_version: "1"
id: "<brain-lesson-id>"
date: "YYYY-MM-DD"
scope: "<scope-string-or-object>"
source: "<source>"
feedback: "<feedback>"
correction: "<correction>"
why: "<why>"
how_to_apply: "<how-to-apply>"
supersedes_ref: "<brain-lesson-id-or-null>"
status: "active"
mediation:
  mode: "merge_time_intent"
  intent_path: ".ce/brain/append-intents/<branch-slug>.yaml"
  intent_sha256: "<64-hex>"
  intent_kind: "lesson_append"
  merge_commit_sha: "<40-hex>"
  pr_number: <integer>
  branch_slug: "<branch-slug>"
  materialization_key: "<64-hex>"
  materialization_record_index: 0
  materialization_record_count: 1
sequence: <integer>
prev_hash: "<64-hex>"
content_hash: "<64-hex>"
```

The record body must not contain execution-time-variable fields such as
`materialization_commit_sha`, wall-clock timestamps, daemon PID, hostname,
credential/account identifiers, retry counters, local paths, or lease holder
identity. Those values may appear only in the commit trailer, PR closeout
comment, and daemon log. This makes byte-identical idempotency verifiable:
given the same live tail, merge commit, intent path, canonical intent SHA-256,
and PR metadata, every instance builds identical record bytes and therefore the
same `content_hash`.

The `materialization_key` persists in two repository-visible places:

- in every appended ledger record's `mediation.materialization_key`;
- in a deterministic trailer line in the materialization commit message:

```text
CE-Materialization-Key: <64-hex>
```

That trailer is mandatory so crash-after-push detection does not need to parse
tree contents before it can identify a candidate materialization commit.

PR closeout comment:

```text
Brain append intent materialized.
intent: .ce/brain/append-intents/<branch-slug>.yaml
intent_sha256: <64-hex>
merge_commit: <40-hex>
materialization_commit: <40-hex>
materialization_key: <64-hex>
ledger_tail: <64-hex>
```

Daemon log:

- Append-only JSON Lines.
- One event per discovery, validation, retry, hold, success, and evidence-emitted
  step.
- Each event includes `materialization_key`, `intent_sha256`,
  `merge_commit_sha`, `main_parent_sha`, result status, and a canonical event
  SHA-256.

The ledger record and commit trailer are durable repository-local evidence. The
PR comment is operator-facing evidence. The daemon log is execution evidence for
audits and crash recovery.

Dry-run/advisory mode, used before direct-write authority is armed, writes no
tracked repository files. It emits JSON to:

```text
.ce/state/brain-intent-materializer/dry-run/<materialization-key>.json
```

The dry-run JSON object has `mode: "dry_run"`, `status`, `intent_path`,
`intent_sha256`, `merge_commit_sha`, `would_append_records`,
`would_remove_intent_path`, `materialization_key`, `ledger_tail_before`,
`ledger_tail_after`, `refusal_reason`, and `generated_patch_sha256`. If the
daemon can comment on the PR, the advisory comment uses this exact form:

```text
Brain append intent dry-run advisory.
status: <would_materialize|held|refused>
intent: .ce/brain/append-intents/<branch-slug>.yaml
materialization_key: <64-hex>
evidence: .ce/state/brain-intent-materializer/dry-run/<materialization-key>.json
```

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

The hard gate name for the intent-XOR-direct-edit rule is
`brain_append_intent_xor_direct_ledger`. It refuses any hybrid PR whose diff
contains both:

- one or more `.ce/brain/append-intents/` files; and
- any edit to `.ce/brain/assertions.yaml`.

The refusal is hard even if the direct ledger edit would otherwise pass the #882
stale-tail gate, because a hybrid PR would create two competing sources of
ledger truth in the same merge.

The materializer, not PR CI, assigns the live `prev_hash` and `content_hash`.

## Scheduled Drill And Test Plan

Unit tests:

- Validate intent schema success and failure cases.
- Verify branch slug must match the file stem and PR branch metadata.
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

4. BLOCKING-FOR-IMPLEMENTATION: What materializer topology is authorized:
   strict singleton under the merge-gate queue daemon, or
   multi-instance-under-external-lock?
   Recommendation: strict singleton for the first armed implementation. A second
   materializer instance is an additional writer to `main`, bears directly on
   Question 1, and requires an external linearizable lock before it can be safe.
