# Feature Specification: Creator Engine Feature 005 — Parallel Controller Orchestration (PCO)

**Feature Branch**: `005-pco-parallel-controller-orchestration`
**Created**: 2026-05-20
**Status**: Draft
**Input**: User description: Creator Engine Feature 005 — define the
parallel-controller orchestration substrate (PCO) that lets multiple
Source-ratified Controllers coordinate isolated lanes of work without
colliding on worktrees, branches, or Assignment Envelopes. Slice 0
delivers the Active-Work Ledger schema, prose protocol, architecture
doc, and validator skeleton; later slices add conflict validation,
worktree allocation, pane registry, side-effect ledger, fan-in
verification, and the canonical-branch integration queue. PCO subsumes
and reshapes the previously-planned Feature 005 dispatch / worktree /
sandbox runtime work.

## User Scenarios & Testing *(mandatory)*

<!--
  Feature 005 PCO is delivered in slices. Slice 0 is a substrate
  feature: schema, prose protocol, architecture doc, and validator
  skeleton, with NO runtime enforcement. Each user story is
  independently testable against the spec, the protocol doc, and the
  validator output, without consulting external systems and without
  running multi-controller writing trials.
-->

### User Story US-0.1 — Controller Records a Claim Before Launching a Parallel Pane (Priority: P1)

A Source-ratified Controller, before launching an Architect or
Implementer pane in a separate worktree, MUST be able to produce a
claim record that validates against
`schemas/active-work-ledger.schema.yaml`. The claim names the
Controller, the lane, the worktree path, the active Assignment
Envelope, the lease duration, the claim timestamp, and the latest
heartbeat timestamp. Without a valid claim record, the Controller
MUST NOT transition the pane to active.

**Why this priority**: Without the claim record, there is no
substrate on which any later slice can detect collisions, allocate
worktrees, or fan-in verify multi-lane authorship. Slice 0 is the
load-bearing primitive for every later PCO slice.

**Independent Test**: A reviewer with `git clone` and the Slice 0
artifacts can write a golden claim record by hand, run
`creator_engine_validator check` (or the dedicated
`scan-active-work-ledger` subcommand), and observe the
`active_work_ledger_schema` check pass.

**Acceptance Scenarios**:

1. **Given** the tracked schema and the prose protocol, **When** a
   Controller authors a claim record with all required fields,
   **Then** the validator's `active_work_ledger_schema` check passes
   for that record.
2. **Given** a Controller about to launch an Architect or Implementer
   pane, **When** the Controller has not produced a valid claim,
   **Then** the protocol forbids the pane transition.
3. **Given** a claim record carrying a forbidden surface (e.g., a
   secret-shaped string under `note`, a model identifier under
   `pane_label`), **When** the validator runs, **Then** the structural
   constraints (`unevaluatedProperties: false`, enum constraints on
   `pane_label`) reject the record.

---

### User Story US-0.2 — Controller Produces Heartbeat and Event Records (Priority: P1)

The same Controller MUST be able to emit heartbeat records and event
records that validate against the same schema. Heartbeats reference
the claim file they update and carry a monotonically non-decreasing
sequence counter; events carry an event kind (one of
`claim_created`, `claim_released`, `claim_lapsed`,
`heartbeat_emitted`, `lane_handoff_announced`,
`lane_handoff_received`), an event id, and an event timestamp.

**Why this priority**: Heartbeats are how Slice 0 records that a
claim is still live; events are how Slice 0 records what happened.
Without these primitives, later slices' conflict validator and
fan-in cannot reconstruct lane activity.

**Independent Test**: A reviewer can write a golden heartbeat record
and a golden event record; the `active_work_ledger_schema` check
passes for both. Dropping a required field or violating a pattern
produces a `PCO-001` failure that cites
`docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md`.

**Acceptance Scenarios**:

1. **Given** the tracked schema, **When** a Controller authors a
   heartbeat record naming an existing claim file, **Then** the
   validator's `active_work_ledger_schema` check passes.
2. **Given** the tracked schema, **When** a Controller authors an
   event record with a valid `event_kind` and `event_id`, **Then**
   the validator passes.
3. **Given** an event record using a forbidden `event_kind` value
   (e.g., `approved_for_merge`), **When** the validator runs, **Then**
   the enum constraint rejects the record with a `PCO-001` failure
   citing the prose contract.

---

### User Story US-0.3 — Invalid Records Fail Validation Cleanly (Priority: P1)

Every schema violation produces an actionable `PCO-001` failure that
names the violated field path, the violation message, and the prose
contract path (`docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md`).
Non-schema structural failures (file not a YAML mapping) produce an
`active_work_ledger_invalid_record` failure to keep schema violations
distinct from structural pre-validation failures.

**Why this priority**: Clean failure modes are how reviewers and
later slices read the validator output. Without them, the substrate
emits noise that later slices' validators cannot build on.

**Independent Test**: A reviewer hand-authors malformed records (bad
`controller_id` pattern, missing `lane_id`, invalid `claimed_at`
timestamp, unknown top-level field, invalid `release_reason` value)
and confirms each one produces the expected failure code and contract
citation.

**Acceptance Scenarios**:

1. **Given** a record missing a required field, **When** the
   validator runs, **Then** a `PCO-001` failure cites the missing
   field and the contract path.
2. **Given** a record with an unknown top-level field, **When** the
   validator runs, **Then** the `unevaluatedProperties: false`
   constraint rejects it.
3. **Given** an orphaned `*.tmp.<pid>.<nonce>` atomic-write temp
   file, **When** the validator runs, **Then** it is skipped without
   error.

---

### User Story US-0.5.1 — Controller Emits a Completion Report for a Ratified Gate (Priority: P1)

The same Controller, when a Source-ratified gate ends, MUST be able
to produce a Completion Report sidecar that validates against
`schemas/completion-report.schema.yaml`. The sidecar carries the
universal fields (`kind`, `schema_version`, `gate_class`,
`envelope_ref`, `envelope_sha256`, `controller_id`, `lane_id`,
`gate_opened_at`, `gate_closed_at`, `outcome`, `summary`,
`recommended_immediate_next_step`, `exact_next_source_prompt`,
`terminal_packet_sections_present`) plus the class-specific fields
required by §g of
[`../../docs/operations/COMPLETION_REPORT_PROTOCOL.md`](../../docs/operations/COMPLETION_REPORT_PROTOCOL.md).
Without a valid sidecar, the gate's return value is undefined runtime
state.

**Why this priority**: The completion-report sidecar is the
deterministic return packet of every ratified gate. It is the
substrate the Slice 0.5R Hermes runtime hook will read. Without it,
later slices have nothing to enforce against.

**Independent Test**: A reviewer can write a golden completion-report
sidecar by hand, run
`creator_engine_validator scan-completion-reports examples/well-formed/completion-reports`,
and observe `PASS completion_report_schema` and
`PASS completion_report_required_for_envelope`.

**Acceptance Scenarios**:

1. **Given** the tracked schema and prose protocol, **When** a
   Controller authors a class-A completion-report sidecar with all
   universal required fields, **Then** the validator's CR-001 check
   passes.
2. **Given** a class-C-merge gate, **When** the Controller authors a
   sidecar embedding the structured `merge_report` object, **Then**
   the CR-001 check passes; the prose ten-field rule from
   `../../docs/delivery/NEXT_TASK_PROTOCOL.md` §b continues to control
   for human review.
3. **Given** a class-F (blocked / aborted) gate, **When** the
   Controller authors a sidecar with `outcome ∈ {blocked, aborted}`,
   `blocker_description`, and `resumption_pointer`, **Then** the
   CR-001 check passes.

---

### User Story US-0.5.2 — Envelope→Report Pairing Validates Mechanically (Priority: P1)

CR-002 (`completion_report_required_for_envelope`) MUST mechanically
verify that, when a completion-report sidecar's `envelope_ref`
resolves to a real file on disk, the file's SHA256 equals the
sidecar's `envelope_sha256`. CR-002 MUST also fail when two
completion-report sidecars with `outcome: completed` reference the
same envelope.

**Why this priority**: CR-002 catches drift between the bytes Source
ratified and the bytes the gate claims to have executed. Without
mechanical pairing, the report's binding to ratification is
documentary, not enforceable.

**Independent Test**: A reviewer can construct two sidecars pointing
at a known file and confirm that the matching-SHA case passes while
the mismatched-SHA case fails with `CR-002`; the bundled
`examples/malformed/completion-reports/mismatched-sha.yaml` fixture
exercises the failure path.

**Acceptance Scenarios**:

1. **Given** a sidecar whose `envelope_ref` does not resolve to any
   file on disk (typical for `.hermes/`-prefixed envelopes), **When**
   CR-002 runs, **Then** the check passes (the envelope is presumed
   to live under the local-runtime ignore).
2. **Given** a sidecar whose `envelope_ref` resolves to a real file
   with a different SHA256, **When** CR-002 runs, **Then** the check
   fails citing `CR-002` and the prose contract.
3. **Given** two sidecars referencing the same envelope, both with
   `outcome: completed`, **When** CR-002 runs, **Then** the check
   fails.

---

### User Story US-0.5.3 — Terminal Sections Are Captured in Canonical Order (Priority: P1)

Per-class Markdown templates under
`templates/hermes/completion-reports/` MUST contain the three literal
terminal section headers `Summary`,
`Recommended immediate next step`, and
`Exact next Source prompt pointer+SHA256` in that canonical order.
CR-003 (`completion_report_terminal_sections`, warn-only in v1)
verifies that adjacent Markdown bodies for each YAML sidecar present
the three headers in the same canonical order.

**Why this priority**: The three section headers are the cross-skill
terminal packet shape the Controller continuity and GitHub-PR
workflow skills already require. Pinning them in templates and in a
warn-only validator gives CI-time defense in depth ahead of the
Slice 0.5R runtime hook.

**Independent Test**: A reviewer can list the six per-class Markdown
templates and confirm each contains the three headers verbatim and
in canonical order; the bundled malformed fixture
`examples/malformed/completion-reports/missing-section-header.md`
exercises the CR-003 warning path.

**Acceptance Scenarios**:

1. **Given** the six per-class Markdown templates (`class-a-ratified-prompt`,
   `class-c-merge`, `class-c-pr-only`, `class-d-runtime-mutation`,
   `class-e-read-only-research`, `class-f-blocked-or-aborted`),
   **When** a reviewer reads each template, **Then** the three
   canonical headers appear verbatim and in canonical order.
2. **Given** a Markdown body that omits one of the three headers,
   **When** CR-003 runs, **Then** the check emits a `CR-003`
   warning citing the missing header(s).

---

### User Story US-0.5.4 — Active-Work Ledger Records Completion-Report Events Additively (Priority: P1)

`schemas/active-work-ledger.schema.yaml` MUST accept
`schema_version: "2"` and the four new `event_kind` values
`gate_opened`, `gate_closed`, `completion_report_emitted`, and
`gate_blocked`, with an optional `details.completion_report_ref`
pointer linking the event to a completion-report sidecar. The
extension MUST be additive: v1 records continue to validate
unchanged.

**Why this priority**: Binding completion-report emission into the
existing Active-Work Ledger event stream avoids a parallel ad-hoc
artifact stream and gives the Slice 0.5R runtime hook a single
source of truth (the ledger) to read.

**Independent Test**: A reviewer can author v2 event records using
each of the four new event kinds and confirm the
`active_work_ledger_schema` check passes; v1 records continue to
pass unchanged.

**Acceptance Scenarios**:

1. **Given** an event record with `schema_version: "2"` and
   `event_kind: gate_opened`, **When** the validator runs, **Then**
   the check passes.
2. **Given** a `completion_report_emitted` event with
   `details.completion_report_ref` pointing at a sidecar path,
   **When** the validator runs, **Then** the check passes.
3. **Given** a `schema_version: "1"` Slice 0 event using only the
   original six event kinds, **When** the validator runs, **Then**
   the check still passes (additive extension).

---

### User Story US-0.5.5 — Slice 0.5 Defers Runtime Enforcement (Priority: P1)

Slice 0.5 is **record/validate only**. The Hermes final-answer /
send-blocking runtime hook is reserved for the follow-on Slice 0.5R
and is ratified separately as a Hermes-side change. The
grandfather-exemption for dangling pre-hook gates is reserved for
Slice 0.5T. The governed-override emergency bypass is reserved for
Slice 0.5G.

**Why this priority**: Keeping authoring and runtime on separate
gates preserves the substrate-before-automation discipline that PCO
Slice 0 established.

**Independent Test**: A reviewer reads
[`../../docs/operations/COMPLETION_REPORT_PROTOCOL.md`](../../docs/operations/COMPLETION_REPORT_PROTOCOL.md)
§n and §o and can name the deferred slices (0.5R / 0.5T / 0.5G)
and the specific Slice 0.5 non-goal each closes.

**Acceptance Scenarios**:

1. **Given** the Slice 0.5 substrate, **When** a Controller emits a
   terminal answer for a ratified gate without an accompanying
   sidecar, **Then** Slice 0.5 does NOT mechanically block the
   answer; the block is reserved for Slice 0.5R.
2. **Given** a dangling pre-hook gate observed in the ledger,
   **When** Slice 0.5 runs, **Then** Slice 0.5 does NOT
   retroactively close it; closure is reserved for Slice 0.5T.

---

### User Story US-2A.1 — Controller Records a Worktree Lease Before Writing a Claim (Priority: P1)

A Source-ratified Controller, before writing an Active-Work Ledger
claim against a physical worktree under multi-Controller conditions,
MUST be able to produce a worktree-lease record that validates
against `schemas/worktree-lease.schema.yaml`. The lease names the
Controller, the lane, the lease id, the worktree path, the
acquisition timestamp, the lease duration, and the expiry timestamp.
Optional fields are `pane_label`, `branch`, `envelope_ref`, and
`note`.

**Why this priority**: Without a tracked lease primitive, contention
between two Source-ratified Controllers is detectable only *after*
both ledger claims hit disk. The lease record closes the
intent-to-write gap that Slice 1/2 left open (G1 in the architect
report).

**Independent Test**: A reviewer with `git clone` and the Slice 2A
artifacts can write a golden lease record by hand, run
`creator_engine_validator scan-worktree-leases examples/well-formed/worktree-leases`,
and observe the `worktree_lease_schema` check pass.

**Acceptance Scenarios**:

1. **Given** the tracked schema and the prose protocol, **When** a
   Controller authors a lease record with all required fields,
   **Then** the validator's `worktree_lease_schema` check passes
   for that record.
2. **Given** a lease record missing a required field (e.g.,
   `lease_id`, `worktree_path`, `acquired_at`, `lease_seconds`, or
   `expires_at`), **When** the validator runs, **Then** a `PCO-020`
   failure cites the missing field and the prose contract
   `docs/operations/WORKTREE_LEASE_PROTOCOL.md`.
3. **Given** a lease record carrying an unknown top-level field,
   **When** the validator runs, **Then** the
   `unevaluatedProperties: false` constraint rejects it with
   `PCO-020`.

---

### User Story US-2A.2 — Live Claim Without a Live Lease Is Refused When Leases Exist (Priority: P1)

When at least one valid `worktree_lease` record is discovered in the
scanned tree, the Slice 1/2 `active_work_ledger_conflicts` validator
MUST refuse any live ledger claim whose `worktree_path` is not
covered by a live (non-expired) lease under the same
`controller_id`. Trees that contain zero `worktree_lease` records
MUST preserve Slice 1/2 behavior unchanged.

**Why this priority**: The predicate is the substrate mechanism by
which a Controller's claim is forced to descend from a prior
intent-to-write. Without backward-compatible gating, every existing
PCO tree would suddenly require a lease.

**Independent Test**: A reviewer can stage a tree with one live
lease covering `/worktrees/example` and one live claim for the same
worktree under the same controller and observe the validator pass;
removing the lease (or expiring it) causes the validator to fail
with `PCO-021`. A tree with no lease records at all continues to
validate identically to Slice 1/2.

**Acceptance Scenarios**:

1. **Given** a tree with one live lease under
   `controller_id: hermes-primary` covering
   `worktree_path: /worktrees/example` and one live ledger claim
   under the same controller for the same worktree, **When**
   `active_work_ledger_conflicts` runs, **Then** the check passes.
2. **Given** a tree with at least one valid lease record but where
   the only live claim names a worktree NOT covered by any live
   lease under that controller, **When** the validator runs, **Then**
   the check fails with `PCO-021` citing the lease prose contract.
3. **Given** a tree with zero `worktree_lease` records, **When** the
   validator runs, **Then** `PCO-021` does NOT fire (backward-
   compatibility floor); Slice 1/2 invariants continue to apply
   unchanged.
4. **Given** a tree with a lease whose `expires_at` is in the past
   and a live claim for the same worktree under the same controller,
   **When** the validator runs, **Then** the check fails with
   `PCO-021` because the lease is no longer live.

---

### User Story US-2A.3 — Cross-Controller Lease Contention Is Refused Before Claims Exist (Priority: P1)

Two live `worktree_lease` records for the same normalized
`worktree_path` under *different* `controller_id` values MUST fail
the Slice 1/2 `active_work_ledger_conflicts` validator with
`PCO-022` (`worktree_lease_conflict`), independently of whether
either side has yet written a ledger claim. This is the
contention-resolution primitive Slice 2A delivers.

**Why this priority**: This is the predicate that lets two
Source-ratified Controllers safely rehearse multi-lane authoring;
without it, contention is only resolvable after a race lands on
disk.

**Independent Test**: A reviewer can stage two live leases under
different controllers for the same `worktree_path` and observe
`PCO-022`; the bundled
`examples/malformed/worktree-leases/cross-controller-conflict/`
fixture exercises this path.

**Acceptance Scenarios**:

1. **Given** two live leases on `/worktrees/shared` under
   `controller_id: hermes-primary` and `controller_id: nefarious-laptop-a`,
   **When** `active_work_ledger_conflicts` runs, **Then** the check
   fails with `PCO-022`.
2. **Given** a structurally invalid lease record surfaced during
   the conflict scan, **When** the validator runs, **Then** a
   `PCO-023` failure surfaces separately from `PCO-020` so the
   schema-validity surface is not silently widened.

---

### User Story US-2A.4 — Slice 2A Defers Allocator Runtime, Pane Registry, and Identity Hardening (Priority: P1)

Slice 2A is **record / validate / refuse only**. It does NOT
allocate worktrees, does NOT mutate `git worktree` state, does NOT
ship a `pco-allocate` / `pco-release` CLI, does NOT introduce a
Hermes runtime hook, does NOT re-enable `pco-completion-gate`, does
NOT add tracked `.hermes/active-work-ledger/` runtime records, and
does NOT solve cryptographic controller-identity binding. Runtime
allocation is reserved for Slice 2R. Identity hardening is reserved
for a separately ratified follow-on workstream (provisionally
"Slice 2.5 — Controller Identity Substrate").

**Why this priority**: Keeping authoring and runtime on separate
gates preserves the substrate-before-automation discipline that
PCO Slice 0, Slice 0.5, and Slice 1/2 each held to.

**Independent Test**: A reviewer reads
[`../../docs/operations/WORKTREE_LEASE_PROTOCOL.md`](../../docs/operations/WORKTREE_LEASE_PROTOCOL.md)
§§c, j, k, l and can name the deferred slices and the specific
Slice 2A non-goal each closes.

**Acceptance Scenarios**:

1. **Given** the Slice 2A substrate, **When** a reviewer searches
   for any `pco-allocate` / `pco-release` entry point or any code
   that calls `git worktree`, **Then** none exists.
2. **Given** the Slice 2A substrate, **When** a reviewer searches
   the validator output for any `pco-completion-gate` mutation,
   **Then** none exists.
3. **Given** the Slice 2A substrate, **When** a reviewer searches
   for any tracked file under `.hermes/active-work-ledger/`,
   **Then** none exists.

---

### User Story US-2.5.1 — Controller Identity Is Bound to a Signing Key Record (Priority: P1)

A Source-ratified Controller, once the Slice 2.5 substrate is
present, MUST hold a tracked **controller-key record** that binds
its `controller_id` to a verifiable public key. The record names the
`controller_id`, the public key material, the key algorithm, the
key issuance timestamp, the issuing identity (per Feature 001
identity contract), and the key custody mode (operator-time decision
per the Open Source Decisions section below). Controller identity is
no longer treated as a forgeable free string once any
controller-key record exists in the scanned tree.

**Why this priority**: Slice 2A
([`docs/operations/WORKTREE_LEASE_PROTOCOL.md`](../../docs/operations/WORKTREE_LEASE_PROTOCOL.md)
§j) flagged forgery risk as operationally material under
multi-Controller rehearsal. Slice 2R productizes the lease layer
into a runtime allocator; without identity hardening, the
allocator's refusal predicates remain forgeable. The key record is
the load-bearing primitive every later identity-scoped check binds
to.

**Independent Test**: A reviewer can author a golden controller-key
record under `tenants/<tenant>/controllers/<controller-id>.key.yaml`
(or the path Source ratifies under PCO-026), run the
`controller_key_schema` validator check, and observe
`PASS controller_key_schema`. A second record with a malformed
public-key block fails with `PCO-025` and cites the prose contract.

**Acceptance Scenarios**:

1. **Given** the tracked controller-key schema and one well-formed
   key record under the agreed-on path, **When** the validator runs,
   **Then** the `controller_key_schema` check passes for that
   record.
2. **Given** a controller-key record whose `controller_id` does not
   match the Slice 0 `^[a-z][a-z0-9-]{2,63}$` pattern, **When** the
   validator runs, **Then** the check fails citing `PCO-025` and the
   prose contract.
3. **Given** a tree with zero controller-key records, **When** the
   validator runs, **Then** the `worktree_lease_signature` predicate
   (`PCO-024`) does NOT fire and existing Slice 2A behavior is
   preserved unchanged (backward-compatibility floor per PCO-026).

---

### User Story US-2.5.2 — Forged Lease and Forged Controller Identity Are Detectable (Priority: P1)

Once at least one controller-key record exists in the scanned tree,
the `active_work_ledger_conflicts` validator MUST run the
`worktree_lease_signature` (`PCO-024`) predicate against every live
`worktree_lease` record. A lease whose embedded signature does not
verify against a known controller-key record for the lease's
`controller_id` MUST fail with `PCO-024`. A lease whose
`controller_id` does not match any known key record MUST also fail
with `PCO-024`. The same predicate makes a forged Active-Work
Ledger claim that descends from an unverifiable lease detectable
through the existing Slice 2A `PCO-021`
(`claim_requires_live_lease`) refusal: a forged claim cannot point
at a verifiable lease, so it is refused upstream.

**Why this priority**: This is the acceptance criterion (A6 in the
architect report §6) that converts the Slice 2A controller-identity
caveat into a mechanically enforceable refusal. Without it, Slice
2R's runtime allocator would productize an unauthenticated
coordination protocol.

**Independent Test**: A reviewer can stage a tree with one
well-formed controller-key record for `hermes-primary`, one
correctly signed lease record under `hermes-primary`, and one lease
record under `hermes-primary` carrying a tampered signature. The
validator passes the first lease and fails the second with
`PCO-024`. A reviewer can also stage a lease under
`controller_id: nefarious-laptop-a` for which no key record exists
and observe `PCO-024` fail with an explicit "no key for
`controller_id`" failure message.

**Acceptance Scenarios**:

1. **Given** a tree with one controller-key record for
   `hermes-primary` and one live lease under `hermes-primary` whose
   embedded signature verifies against that key, **When**
   `active_work_ledger_conflicts` runs, **Then** `PCO-024` passes
   for that lease.
2. **Given** the same tree but with a second lease whose signature
   does not verify, **When** the validator runs, **Then** `PCO-024`
   fails for the second lease citing
   `docs/operations/WORKTREE_LEASE_PROTOCOL.md` §j and the
   controller-key contract.
3. **Given** a lease record under a `controller_id` for which no
   key record exists in the scanned tree, **When** the validator
   runs, **Then** `PCO-024` fails with an explicit
   "unknown controller key" message.
4. **Given** a tree with zero controller-key records, **When** the
   validator runs, **Then** `PCO-024` does NOT fire on any lease
   (backward-compatibility floor; Slice 2A behavior is preserved).

---

### User Story US-2R.1 — Allocator Refuses Before `git worktree add` Under Cross-Controller Contention (Priority: P1)

The `pco-allocate` CLI, given an Assignment Envelope reference and a
target lane id, MUST run the `active_work_ledger_conflicts`
validator against the tracked + local-runtime state **before**
issuing any `git worktree add` command. If the validator would
refuse the resulting state (specifically: a live lease under another
`controller_id` already covers the same normalized `worktree_path`
per `PCO-022`, or an existing live claim on the worktree under
another `controller_id` per `PCO-010`), the allocator MUST exit
non-zero, cite the failing predicate by code, and leave the working
tree and local-runtime directories untouched.

**Why this priority**: This is acceptance criterion A1 from the
architect report. It is the predicate that turns Slice 2A's paper
refusal into a runtime block on collision. Without it, the allocator
could produce a half-allocated worktree on contention.

**Independent Test**: A reviewer can stage a tree with a live lease
under `nefarious-laptop-a` for `/worktrees/example`, then invoke
`pco-allocate --envelope <path> --lane example-lane` as
`hermes-primary`. The CLI exits non-zero, cites `PCO-022` (or
`PCO-010` if the contention is at the claim layer), and no
`git worktree` mutation is observable.

**Acceptance Scenarios**:

1. **Given** a tree with a live lease for `/worktrees/example`
   under `controller_id: nefarious-laptop-a`, **When**
   `pco-allocate` runs as `hermes-primary` requesting the same
   worktree path, **Then** the CLI exits non-zero before any
   `git worktree add` is attempted and cites `PCO-022`.
2. **Given** a tree with a live ledger claim on
   `/worktrees/example` under
   `controller_id: nefarious-laptop-a` but no lease (Slice 1/2
   contention), **When** `pco-allocate` runs as `hermes-primary`,
   **Then** the CLI exits non-zero before allocation and cites
   `PCO-010`.
3. **Given** the same tree, **When** the operator inspects
   `git worktree list` after the refused allocation, **Then** no
   new worktree appears.

---

### User Story US-2R.2 — Allocator Performs Lease + Claim + Event Atomically (Priority: P1)

When the pre-launch validator passes, `pco-allocate` MUST perform
the following operations **atomically under an exclusive advisory
lock** on `locks/<lane-id>.lock` (per Slice 0 PCO-009): (a) issue
`git worktree add` to materialize the target worktree, (b) write a
new `worktree_lease` record covering the new worktree, (c) write a
new Active-Work Ledger `claim` record bound to the lease, and (d)
emit a `claim_created` event record per Slice 0 PCO-006. On any
failure mid-sequence, the allocator MUST roll back partial state so
that the tree is observably indistinguishable from the pre-allocate
state (no orphan worktree, no orphan lease, no orphan claim, no
orphan event).

**Why this priority**: This is acceptance criterion A2. The
atomicity invariant is what lets later slices (pane registry,
side-effect ledger, fan-in) treat the lease+claim+event triple as
a single substrate primitive rather than three independently
auditable artifacts that may disagree.

**Independent Test**: A reviewer can simulate a failure injected
between steps (b) and (c) using a controlled fault hook in
`pco-allocate`'s test harness, then run the conflict validator and
inspect `git worktree list`; no partial state is visible. A
successful allocation produces a lease + claim + event that all
reference each other consistently and that validate against their
respective schemas.

**Acceptance Scenarios**:

1. **Given** a clean tree and a passing pre-launch check, **When**
   `pco-allocate` succeeds, **Then** a new worktree, a new lease, a
   new claim, and a new `claim_created` event all exist and
   cross-reference correctly.
2. **Given** a controlled fault after step (b) (lease written) but
   before step (c) (claim written), **When** the allocator rolls
   back, **Then** the lease record is removed, no worktree directory
   remains, and no event is emitted.
3. **Given** a controlled fault after step (a) (`git worktree add`
   succeeded) but before step (b), **When** the allocator rolls
   back, **Then** `git worktree remove` is invoked on the
   not-yet-leased worktree path.
4. **Given** two `pco-allocate` invocations targeting the same
   `lane_id` running concurrently, **When** both attempt the
   sequence, **Then** the advisory lock on `locks/<lane-id>.lock`
   serializes them; one succeeds, the other refuses cleanly.

---

### User Story US-2R.3 — Claim Writes Require a Held Lease; Pane Launch Is Gated; Root Checkout Invariant Holds (Priority: P1)

The Slice 2R runtime MUST enforce three additional invariants
beyond the allocator's happy path:

1. **Claim-writes-only-under-held-lease**: any code path (including
   `pco-allocate` rollback retries and any future Hermes runtime
   hook) that attempts to write a new Active-Work Ledger claim
   record MUST first read a live `worktree_lease` under the writer's
   `controller_id` covering the claim's `worktree_path`. Writes
   without a held lease MUST be refused. This is the runtime
   counterpart to Slice 2A's `PCO-021` paper refusal.
2. **Pre-launch refusal on conflict-validator failure**: any pane
   launch path that consumes a claim (Architect or Implementer pane
   spawn driven by Hermes or by the operator) MUST refuse to spawn
   the pane when `active_work_ledger_conflicts` would refuse the
   current state. The launch refusal MUST cite the failing
   predicate by code (`PCO-010`, `PCO-021`, `PCO-022`, `PCO-024`,
   etc.) and MUST emit a `gate_blocked` event per Slice 0.5
   PCO-014.
3. **Root checkout invariant preservation**: `pco-allocate` and
   `pco-release` MUST refuse to operate when the controller's
   current working directory is the root checkout
   (per
   [`../../docs/operations/ROOT_WORKTREE_INVARIANT.md`](../../docs/operations/ROOT_WORKTREE_INVARIANT.md)).
   The root checkout is reserved for Source-supervised mutations;
   the allocator's job is to create and release isolated worktrees,
   not to mutate the root.

**Why this priority**: These are acceptance criteria A3
(claim-writes-only-under-held-lease) and A4 (pane launch is gated)
from the architect report, plus the root checkout invariant that
Slice 2A explicitly preserves and that the runtime allocator must
not violate.

**Independent Test**: A reviewer can (a) attempt to write a claim
record via a small repro script without holding a lease and observe
the runtime refusal; (b) stage a tree whose conflict validator
fails, attempt to launch a pane, and observe the launch refused
with a `gate_blocked` event; (c) invoke `pco-allocate` from inside
the root checkout and observe the refusal citing
`ROOT_WORKTREE_INVARIANT.md`.

**Acceptance Scenarios**:

1. **Given** a `controller_id: hermes-primary` with no live lease
   for `/worktrees/example`, **When** any path under Slice 2R
   attempts to write a claim for `/worktrees/example`, **Then** the
   write is refused at runtime citing `PCO-021`.
2. **Given** a tree whose `active_work_ledger_conflicts` validator
   would refuse the current state, **When** an operator attempts to
   launch an Architect pane bound to the failing claim, **Then**
   the pane is not spawned, the failing predicate code is reported,
   and a `gate_blocked` event is emitted per PCO-014.
3. **Given** an operator who invokes `pco-allocate` from the root
   checkout, **When** the CLI starts, **Then** it exits non-zero
   citing the root-worktree invariant and performs no mutation.
4. **Given** a successful allocation followed by a `pco-release`
   call, **When** `pco-release` runs, **Then** it (a) removes the
   lease, (b) marks the claim released with a `release_reason`,
   (c) emits a `claim_released` event, and (d) invokes
   `git worktree remove` on the allocated worktree path — all
   atomically under the same lane lock.

---

### User Story US-2R.4 — Slice 2R Does NOT Expand Autonomy or Subsume Later Slices (Priority: P1)

Slice 2R is **runtime allocation only**. It does NOT introduce a
pane registry (Slice 3), does NOT introduce a side-effect ledger
(Slice 4), does NOT introduce multi-lane fan-in (Slice 5), does NOT
introduce an integration queue (Slice 6), does NOT introduce a
tracker / GitHub-issue connector (Feature 008), does NOT
re-enable `pco-completion-gate` (Slice 0.5R), and does NOT
authorize fully autonomous multi-controller or cross-workstation
operation. Each later slice is named and remains separately
ratified.

**Why this priority**: The substrate-before-automation discipline
that PCO Slice 0, 0.5, 1/2, and 2A each held to MUST hold across
Slice 2.5 + 2R. Productizing the allocator while expanding
autonomy in the same gate would freeze a wrong protocol into code.

**Independent Test**: A reviewer reads the spec and the architecture
companion ([`../../docs/architecture/parallel-controller-orchestration.md`](../../docs/architecture/parallel-controller-orchestration.md))
and can name the deferred slices (3, 4, 5, 6, 0.5R) and the specific
Slice 2R non-goal each closes.

**Acceptance Scenarios**:

1. **Given** the Slice 2R substrate, **When** a reviewer searches
   for a tracked pane-registry record schema, **Then** none exists
   (Slice 3).
2. **Given** the Slice 2R substrate, **When** a reviewer searches
   for a tracked side-effect-evidence record schema, **Then** none
   exists (Slice 4).
3. **Given** the Slice 2R substrate, **When** a reviewer searches
   for any GitHub / Jira / Linear connector code, **Then** none
   exists (Feature 008, deferred).
4. **Given** the Slice 2R substrate, **When** a reviewer searches
   for any re-enabled `pco-completion-gate` runtime hook, **Then**
   none exists (Slice 0.5R, separately ratified).

---

### User Story US-0.4 — Slice 0 Does Not Yet Enforce Execution (Priority: P1)

The spec, the protocol doc, and the architecture doc explicitly state
the Slice 0 boundary: **records and validates only; does not yet
enforce multi-controller execution, does not yet detect cross-lane
semantic conflicts, and does not yet allocate worktrees.** Each later
slice that closes the corresponding gap is named.

**Why this priority**: The boundary statement is what keeps Slice 0
auditable. Without it, reviewers cannot tell which behaviors are
substrate (in scope) and which are runtime (out of scope).

**Independent Test**: A reviewer reads the spec, the protocol doc,
and the architecture doc and can list the seven PCO slices and the
specific later-slice gap that closes each Slice 0 non-goal.

**Acceptance Scenarios**:

1. **Given** two valid claim records that collide on `worktree_path`
   under different `controller_id` values, **When** the validator
   runs, **Then** the `active_work_ledger_schema` check does NOT
   flag the collision; the boundary statement and the spec's
   deferral rationale name Slice 1 (Conflict Validator) as the slice
   that closes this gap.
2. **Given** a stale claim (heartbeat older than `lease_seconds`),
   **When** the validator runs, **Then** the `active_work_ledger_schema`
   check does NOT reclaim or fail the claim; staleness is advisory
   in Slice 0.
3. **Given** the spec, **When** a reviewer reads the slice plan,
   **Then** Slices 1 through 6 are each named with a one-sentence
   scope summary and the Slice 0 non-goal they close.

---

## Functional Requirements

Slice 0 functional requirements are numbered `PCO-NNN`. Slice 0 ships
exactly one validator-registered FR (`PCO-001`); the others are
protocol/spec text that later slices will bind to validator checks.

### PCO-001 — Active-Work Ledger Record Schema

The tracked schema at `schemas/active-work-ledger.schema.yaml` defines
the Active-Work Ledger record contract: top-level `kind`,
`record_type`, `schema_version`, `controller_id`, `lane_id`,
`record_timestamp`, plus the `oneOf` per-record-type required-field
sets for `claim`, `heartbeat`, and `event`. The
`active_work_ledger_schema` validator check validates one record at
a time against this schema.

### PCO-002 — Controller Id Format

`controller_id` MUST match `^[a-z][a-z0-9-]{2,63}$` and MUST NOT
embed secrets, tokens, installation ids, durable actor ids, model
identifiers, or account names. Concrete bindings remain
deployment-time overlay decisions per
`docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md` §c precedent.

### PCO-003 — Lane Id Format

`lane_id` MUST match `^[a-z][a-z0-9-]{2,63}$`. Recommended convention
is `<feature-or-slice>-<short-suffix>`; Slice 0 does not enforce
structure beyond the pattern.

### PCO-004 — Claim Record Fields

A claim record (`record_type: claim`) MUST carry the shared envelope
plus `worktree_path`, `envelope_ref`, `lease_seconds`, `claimed_at`,
and `last_heartbeat_at`. Optional fields are `branch`,
`handoff_ref`, `recommended_prompt_ref`, `pane_label`, `released_at`,
and `release_reason`. When `released_at` is present, `release_reason`
MUST also be present.

### PCO-005 — Heartbeat Record Fields

A heartbeat record (`record_type: heartbeat`) MUST carry the shared
envelope plus `claim_ref`, `heartbeat_sequence` (integer `>= 0`), and
`emitted_at`. Optional field is `note` (`maxLength: 1024`). Slice 0
validates the lower bound and type of `heartbeat_sequence` only;
cross-record monotonicity is reserved for later slices.

### PCO-006 — Event Log Record Fields

An event record (`record_type: event`) MUST carry the shared envelope
plus `event_kind` (enum: `claim_created`, `claim_released`,
`claim_lapsed`, `heartbeat_emitted`, `lane_handoff_announced`,
`lane_handoff_received`), `event_id` (pattern
`^[a-z0-9][a-z0-9-]{2,63}$`), and `event_timestamp`. Optional fields
are `subject_claim_ref`, `subject_handoff_ref`, and `details` (a
structured object with `summary` and `actor_pane_label`).

### PCO-007 — Lease / Stale-Record Semantics

`lease_seconds` MUST be an integer in `[60, 86400]`; default is
`3600` (one hour) per protocol convention. A claim is stale when
`now - last_heartbeat_at > lease_seconds`. Slice 0 treats stale
records as **advisory only**; reclamation is reserved for later
slices.

### PCO-008 — Atomic Write Contract

Writers MUST use the temp-file + `fsync(2)` + `rename(2)` pattern
(`<target>.tmp.<pid>.<nonce>` → fsync → rename over `<target>`). The
validator MUST tolerate orphaned `*.tmp.*` files by skipping them.

### PCO-009 — Advisory Lock Contract

Writers MUST hold an exclusive advisory lock on
`locks/<lane-id>.lock` via `flock(LOCK_EX)` around every
read-modify-write sequence touching that lane's claim or heartbeat
files. Slice 0 documents the discipline; runtime tooling that
performs the locking is a later-slice concern.

### PCO-010 — Pre-Launch Claim Read/Validate Contract

Before launching an Architect or Implementer pane, a Controller MUST
enumerate live claims, validate every read claim file against the
schema, run the `active_work_ledger_conflicts` pre-launch check,
refuse to claim a `worktree_path` already held by a live claim under a
different `controller_id`, write the new claim atomically under the
lane lock, and emit a `claim_created` event. The Slice 1/2 validator
mechanically enforces the read-only refusal predicates; worktree
allocation and pane launch orchestration remain later-slice scope.

### PCO-011 — Slice 0 Boundary Statement (No Enforcement)

Slice 0 records and validates Active-Work Ledger entries; it does
NOT yet enforce multi-controller execution, does NOT yet detect
cross-lane semantic conflicts, and does NOT yet allocate worktrees.
This statement MUST appear normatively in the schema description,
the prose protocol, the architecture doc, and this spec.

### PCO-012 — Relationship to Assignment Envelopes and Handoffs

Every claim record MUST carry `envelope_ref` (or the literal `none`
for coordination lanes without an envelope) and MAY carry
`handoff_ref` and `recommended_prompt_ref`. The envelope, not the
ledger, remains the substantive authority; ledger records never
replace handoff content. Pointer-only relay per
[`../../docs/operations/NO_COPY_PASTE_PATTERN.md`](../../docs/operations/NO_COPY_PASTE_PATTERN.md)
applies.

### CR-001 — Completion Report Schema (Slice 0.5)

The tracked schema at `schemas/completion-report.schema.yaml`
defines the Completion Report contract: universal required fields
(per
[`../../docs/operations/COMPLETION_REPORT_PROTOCOL.md`](../../docs/operations/COMPLETION_REPORT_PROTOCOL.md)
§f), per-class conditional fields (§g), and the
`exact_next_source_prompt` shape (§i.2). The
`completion_report_schema` validator check validates one sidecar
at a time against this schema.

### CR-002 — Envelope→Report Pairing (Slice 0.5)

The `completion_report_required_for_envelope` validator check MUST
verify that, when a completion-report sidecar's `envelope_ref`
resolves to a real file in the scanned tree, the file's SHA256
equals `envelope_sha256`; and MUST fail when more than one sidecar
references the same envelope with `outcome: completed`. The
canonical envelope→report cardinality is "at most one completed
report per ratified envelope."

### CR-003 — Terminal Section Headers (Slice 0.5, warn-only)

The `completion_report_terminal_sections` validator check MUST
verify that, when a completion-report Markdown body is present
adjacent to its YAML sidecar, the body contains the three literal
section headers `Summary`,
`Recommended immediate next step`, and
`Exact next Source prompt pointer+SHA256` in that canonical order.
CR-003 emits warnings, not errors, in v1; the primary enforcer is
the Slice 0.5R Hermes runtime hook.

### PCO-014 — Active-Work Ledger Additive Event Extension (Slice 0.5)

`schemas/active-work-ledger.schema.yaml` MUST additively accept
`schema_version: "2"` and four new `event_kind` values:
`gate_opened`, `gate_closed`, `completion_report_emitted`, and
`gate_blocked`. The optional `details.completion_report_ref`
pointer MAY appear under any `event_kind` and matches the same
filename pattern used elsewhere in the schema. The extension is
additive: Slice 0 v1 records continue to validate unchanged.

### PCO-015 — Slice 0.5 Boundary Statement (No Runtime Enforcement)

Slice 0.5 records and validates completion-report sidecars and
extends the Active-Work Ledger schema additively; it does NOT yet
implement the Hermes final-answer / send-blocking runtime hook
(Slice 0.5R), does NOT yet retroactively close dangling pre-hook
gates (Slice 0.5T), and does NOT yet implement the governed-override
emergency bypass (Slice 0.5G). This statement MUST appear normatively
in the schema description, the prose protocol, and this spec.

### PCO-013 — Relationship to One-Driver-Per-Worktree

A claim MUST name exactly one physical `worktree_path` and exactly
one driving `controller_id`. Two live (non-stale) claims for the same
`worktree_path` under different `controller_id` values is a
substrate-level conflict that Slice 1/2's
`active_work_ledger_conflicts` validator MUST reject before launch;
`active_work_ledger_schema` still records the data and validates each
record independently.

### PCO-014 — Claim and Event Reference Integrity

Heartbeat records MUST reference a discovered claim record via
`claim_ref`. Event records that carry `subject_claim_ref` MUST
reference a discovered claim record. The pre-launch conflict validator
MUST fail unresolved references without duplicating one-record schema
semantics.

### PCO-015 — Live Lane Uniqueness

Among non-stale, unreleased claim records, `(controller_id, lane_id)`
MUST identify exactly one live claim. A duplicate live lane under the
same controller is a pre-launch conflict even when the two records name
different worktrees.

### PCO-016 — Heartbeat Sequence Monotonicity

For heartbeat records that reference the same claim and whose
`emitted_at` values are parseable timestamps, `heartbeat_sequence` MUST
be monotonically non-decreasing in emitted-time order. Source-controlled
or commit-based timestamps remain structurally valid, but the
cross-record monotonicity check is advisory/skipped until a comparable
time axis exists.

### PCO-017 — Event-ID Scoped Uniqueness

Event `event_id` values MUST be unique within `(controller_id, lane_id,
YYYY-MM-DD)` when `event_timestamp` can be resolved to a UTC day. This
prevents duplicate event lifecycle records inside the scope already
named by the schema.

### PCO-020 — Worktree Lease Record Schema (Slice 2A)

The tracked schema at `schemas/worktree-lease.schema.yaml` defines
the Worktree Lease record contract: top-level `kind`
(`worktree-lease-record`), `record_type` (`worktree_lease`),
`schema_version` (`"1"`), `controller_id`, `lane_id`,
`record_timestamp`, and the required lease-specific fields
`lease_id`, `worktree_path`, `acquired_at`, `lease_seconds`,
`expires_at`. Optional fields are `pane_label`, `branch`,
`envelope_ref`, and `note`. `unevaluatedProperties: false`. The
`worktree_lease_schema` validator check validates one record at a
time against this schema and cites
`docs/operations/WORKTREE_LEASE_PROTOCOL.md`.

### PCO-021 — Claim Requires Live Worktree Lease (Slice 2A)

When at least one valid `worktree_lease` record is discovered in the
scanned tree, the `active_work_ledger_conflicts` validator MUST
refuse any live ledger claim whose normalized `worktree_path` is not
covered by a live (non-expired) lease under the same
`controller_id`. The predicate is gated on the discovery of a valid
lease record so trees with zero lease records preserve Slice 1/2
behavior unchanged.

### PCO-022 — Cross-Controller Worktree Lease Conflict (Slice 2A)

Two live `worktree_lease` records for the same normalized
`worktree_path` under *different* `controller_id` values MUST fail
the `active_work_ledger_conflicts` validator with
`worktree_lease_conflict`, independently of whether either
controller has yet written a ledger claim. This is the
contention-resolution predicate Slice 2A delivers.

### PCO-023 — Worktree Lease Invalid Record (Slice 2A)

A structurally invalid worktree-lease record discovered during the
conflict scan MUST surface as `worktree_lease_invalid_record`
(`PCO-023`) so the schema-validity surface is not silently widened
by the conflict layer. Schema-level validation of single lease
records is owned by `worktree_lease_schema` (`PCO-020`); resolve
`PCO-020` first when both fire.

### PCO-019 — Slice 2A Boundary Statement (No Allocator, No Runtime)

Slice 2A records, validates, and refuses Worktree Lease state; it
does NOT yet allocate worktrees, does NOT mutate `git worktree`
state, does NOT ship a `pco-allocate` / `pco-release` CLI, does NOT
introduce a Hermes runtime hook, does NOT re-enable
`pco-completion-gate`, does NOT add tracked
`.hermes/active-work-ledger/` runtime records, and does NOT solve
cryptographic controller-identity binding. Runtime allocation is
reserved for Slice 2R. Identity hardening is reserved for a
separately ratified follow-on workstream (Slice 2.5 — Controller
Identity Substrate, paired with Slice 2R in the same gate per
PCO-024 / PCO-027 below). This statement MUST appear normatively in
the schema description, the prose protocol, the architecture doc,
and this spec.

The number `PCO-024` previously cited for this boundary statement is
re-allocated to the Slice 2.5 `worktree_lease_signature` validator
predicate below; the boundary statement itself is renumbered as
`PCO-019` (a previously unused number in the PCO-NNN sequence) and
its semantic content is unchanged.

### PCO-018 — Slice 1/2 Validator Discoverability

The validator registry and CLI MUST expose the Slice 1/2 check as
`active_work_ledger_conflicts`, while preserving
`active_work_ledger_schema` as the one-record Slice 0 schema check.
A focused CLI path such as
`creator_engine_validator scan-active-work-ledger-conflicts <path>` MAY
run the pre-launch layer alone.

### PCO-024 — Worktree Lease Signature Predicate (Slice 2.5)

The `active_work_ledger_conflicts` validator MUST gain a new refusal
predicate, `worktree_lease_signature` (`PCO-024`), that fires once
at least one controller-key record exists in the scanned tree.
`PCO-024` MUST fail a live `worktree_lease` record when (a) its
`controller_id` matches no controller-key record in the scanned
tree, or (b) its embedded signature does not verify against the
public key of the matching controller-key record. Trees with zero
controller-key records MUST preserve Slice 2A behavior unchanged
(backward-compatibility floor; see PCO-026).

The signature field on `worktree_lease` records is introduced
additively under `schemas/worktree-lease.schema.yaml`
`schema_version: "2"`; Slice 2A v1 leases continue to validate
unchanged in trees with zero key records. The exact
serialization shape (canonical byte form over which the signature is
computed, signature encoding, algorithm identifier) is a Slice 2.5
schema-authoring concern and is bound by PCO-025 below; this spec
fixes the predicate name and intent only.

### PCO-025 — Controller-Key Record Schema (Slice 2.5)

The tracked schema (provisionally
`schemas/controller-key.schema.yaml`) defines the controller-key
record contract: top-level `kind: controller-key-record`,
`record_type: controller_key`, `schema_version: "1"`,
`controller_id` (Slice 0 pattern `^[a-z][a-z0-9-]{2,63}$`),
`public_key` (PEM or equivalent canonical encoding chosen at
schema-authoring time), `key_algorithm` (e.g., `ed25519`),
`issued_at` (ISO-8601 UTC), `issued_by` (a Feature 001 identity
record pointer), and `key_custody_mode` (one of the operator-time
decision values ratified per the Open Source Decisions section
below). `unevaluatedProperties: false`. The
`controller_key_schema` validator check validates one record at a
time against this schema and cites the new prose contract
(provisionally `docs/operations/CONTROLLER_IDENTITY_PROTOCOL.md`).

Slice 2.5 is **substrate-only** at the key-record layer:
key generation, distribution, custody, and rotation remain
operator-time decisions. The schema enforces shape only. No
mechanical refusal predicate fires from `controller_key_schema`
alone beyond malformed-record detection; the cross-record predicate
that binds keys to leases is `PCO-024` above.

### PCO-026 — Slice 2.5 Backward-Compatibility Floor

`PCO-024` (`worktree_lease_signature`) MUST be gated on the
discovery of at least one valid controller-key record in the
scanned tree. Trees with zero controller-key records MUST validate
identically to Slice 2A: lease records without a signature field
continue to pass `PCO-020`; `active_work_ledger_conflicts` runs
`PCO-021` / `PCO-022` / `PCO-023` exactly as today; the absence of
a signature is not a `PCO-024` failure when no key substrate is
present.

This floor mirrors the gating discipline Slice 2A applied to
`PCO-021` (`claim_requires_live_lease`): every additive substrate
layer ships with an explicit zero-state behavior so the validator
does not retroactively refuse every prior PCO tree.

### PCO-027 — `pco-allocate` CLI Responsibilities (Slice 2R)

`pco-allocate <envelope-ref> --lane <lane-id> [--branch <branch>]
[--worktree-path <path>]` is the Slice 2R runtime entry point. Its
responsibilities are exactly:

1. Refuse to run from the root checkout per
   [`../../docs/operations/ROOT_WORKTREE_INVARIANT.md`](../../docs/operations/ROOT_WORKTREE_INVARIANT.md).
2. Resolve the target `controller_id` from the local Controller
   identity context.
3. Acquire an exclusive advisory `flock(LOCK_EX)` on
   `.hermes/active-work-ledger/locks/<lane-id>.lock` for the
   duration of the allocation.
4. Run `active_work_ledger_conflicts` against the current tree +
   the **proposed** post-allocation state. Exit non-zero with the
   failing predicate cited if the validator would refuse.
5. Atomically: issue `git worktree add` for the target path; write
   a `worktree_lease` record (PCO-020-shape, plus PCO-024 signature
   field when a key substrate is present); write an Active-Work
   Ledger `claim` record (PCO-004-shape) bound to the lease; emit a
   `claim_created` event (PCO-006-shape).
6. On any mid-sequence failure: roll back partial state so that
   the tree is observably indistinguishable from the pre-allocate
   state.
7. Release the advisory lock.

`pco-allocate` MUST NOT mutate `origin/main`, MUST NOT push, MUST
NOT create PRs, MUST NOT mutate GitHub state, MUST NOT mutate
tracker state, and MUST NOT mutate any tracked file under the root
checkout. All mutations are scoped to the new worktree and to local
runtime under `.hermes/active-work-ledger/`.

### PCO-028 — `pco-release` CLI Responsibilities (Slice 2R)

`pco-release <claim-ref-or-lane-id>` is the Slice 2R teardown
entry point. Its responsibilities are exactly:

1. Refuse to run from the root checkout per the same invariant.
2. Acquire the lane lock as in PCO-027.
3. Atomically: mark the claim released (write `released_at` and
   `release_reason` per PCO-004); remove the lease record; emit a
   `claim_released` event (PCO-006); invoke `git worktree remove`
   on the worktree path.
4. On mid-sequence failure: leave a recoverable state that
   `pco-release` can be re-invoked against; never leave an orphan
   lease without a released claim.
5. Release the advisory lock.

`pco-release` MUST NOT delete or rename branches and MUST NOT push.
Branch lifecycle remains operator-controlled and Source-ratified.

### PCO-029 — Claim-Writes-Only-Under-Held-Lease Runtime Enforcement (Slice 2R)

Any code path that writes a new Active-Work Ledger claim record
under Slice 2R (including `pco-allocate`, future Hermes runtime
hooks, and any operator script that uses the Slice 2R runtime
library) MUST first read a live `worktree_lease` record under the
writer's `controller_id` covering the claim's normalized
`worktree_path`. Writes without a held lease MUST be refused at
runtime, citing `PCO-021`. This is the runtime counterpart to Slice
2A's `PCO-021` paper refusal; the Slice 1/2 + 2A validators remain
the static refusal layer, while PCO-029 is the active layer.

### PCO-030 — Pane Launch Is Gated by `active_work_ledger_conflicts` (Slice 2R)

Any pane launch path that consumes a Slice 0 claim — Architect or
Implementer pane spawn driven by Hermes, by `pco-allocate`'s
post-allocate spawn hook (if any), or by an operator script — MUST
refuse to spawn the pane when `active_work_ledger_conflicts` would
refuse the current state. The launch refusal MUST cite the failing
predicate by code and MUST emit a `gate_blocked` event per Slice
0.5 (`PCO-014` Active-Work Ledger Additive Event Extension). The
gating discipline applies to every predicate in the conflict
validator's surface: `PCO-010`, `PCO-014` (reference integrity),
`PCO-015` (live lane uniqueness), `PCO-016` (heartbeat
monotonicity), `PCO-017` (event-id uniqueness), `PCO-021`,
`PCO-022`, `PCO-023`, and `PCO-024`.

### PCO-031 — Root Checkout Invariant Preservation (Slice 2R)

`pco-allocate` and `pco-release` MUST refuse to operate when the
controller's current working directory is the root checkout (per
[`../../docs/operations/ROOT_WORKTREE_INVARIANT.md`](../../docs/operations/ROOT_WORKTREE_INVARIANT.md)).
The root checkout is reserved for Source-supervised mutations; the
allocator's job is to create and release isolated worktrees, not to
mutate the root. This invariant is independent of `PCO-027` /
`PCO-028` step ordering: it MUST be enforced before any other
allocator action, and it MUST be enforced before any non-trivial
side effect (no `git worktree add`, no lease write, no claim write,
no event emission may precede the invariant check).

### PCO-032 — Slice 2.5 + 2R Boundary Statement (No Autonomy Expansion)

Slice 2.5 introduces a tracked controller-key substrate and an
additive `worktree_lease_signature` predicate; Slice 2R introduces
the `pco-allocate` / `pco-release` runtime allocator. Together they
do NOT introduce a pane registry (Slice 3), do NOT introduce a
side-effect ledger (Slice 4), do NOT introduce multi-lane fan-in
(Slice 5), do NOT introduce a canonical-branch integration queue
(Slice 6), do NOT introduce a tracker / GitHub-issue connector
(Feature 008 in the architect report's team-mode roadmap), do NOT
re-enable `pco-completion-gate` (Slice 0.5R), do NOT introduce
distributed identity (Feature 009 in the architect report), do NOT
introduce a Project Coordination Ledger (Feature 007 / TM-1 in the
architect report), and do NOT authorize fully autonomous
multi-controller or cross-workstation operation. The paired slice
is **local-solo-developer runtime hardening**; team-mode operation
remains a later, separately ratified workstream.

This statement is normative. It MUST appear in this spec, in the
companion architecture doc when Slice 2.5 + 2R land, and in the
prose protocol(s) the implementation slice writes.

### PCO-046 — Pane Registry Record Schema (Slice 3, reserved)

The future tracked schema (provisionally
`schemas/pane-registry.schema.yaml`) defines the Pane Registry record
contract: top-level `kind` (`pane-registry-record`), `record_type`
(`pane_identity`), `schema_version` (`"1"`), `controller_id`,
`lane_id`, `claim_ref`, `host_id`, `pane_id`, `role`, `status`,
`record_timestamp`, `registered_at`, and `last_seen_at`. Optional
fields are `claim_record_sha256`, `closed_at`, `close_reason`,
`terminal`, `worktree_path`, `branch`, `envelope_ref`, `handoff_ref`,
`recommended_prompt_ref`, `container_instance_id`, and
`container_instance_ref`. Runtime records live under
`.hermes/active-work-ledger/panes/<controller-id>/<lane-id>.yaml`
and remain ignored local runtime state. The future
`pane_registry_schema` validator check validates one record at a
time and cites
[`../../docs/operations/PANE_REGISTRY_PROTOCOL.md`](../../docs/operations/PANE_REGISTRY_PROTOCOL.md).

### PCO-047 — Pane Registry Id Formats (Slice 3, reserved)

Pane Registry `controller_id` and `lane_id` use the same formats and
caveats as the Active-Work Ledger. `host_id` and `pane_id` MUST be
stable non-secret identifiers sufficient to distinguish panes on one
host without embedding secrets, durable account ids, model names, or
provider/tool authority.

### PCO-048 — Pane Registry Role and Status Enums (Slice 3, reserved)

Pane Registry roles are `architect`, `implementer`, `reviewer`, and
`verification` unless a later Source-ratified protocol amendment
justifies an addition. These roles identify visible-pane function and
are distinct from Slice 2I-S worker-container policy roles
(`architect_research`, `implementer`, `verification`). Status values
are `starting`, `active`, `blocked`, `closing`, `closed`, and
`aborted`; terminal statuses require `closed_at` and `close_reason`.

### PCO-049 — Operator-Visible Tmux Identity (Slice 3, reserved)

When a Pane Registry record claims `visibility: operator_visible` or
equivalent visible/operator-supervised compliance, the future
validator MUST require `terminal.kind: tmux` with `session_id`,
`window_id`, and `pane_id`. `plain_terminal` and `unknown` are
transitional or legacy evidence categories only and do not satisfy
visible/operator-supervised compliance.

### PCO-050 — Active Pane Requires Live Claim (Slice 3, reserved)

An `active`, `blocked`, or `closing` Pane Registry record MUST bind
to a discovered unreleased Active-Work Ledger claim whose
`controller_id`, `lane_id`, and `claim_ref` match the pane record.
The Pane Registry does not replace claim lifecycle authority; it
records pane identity bound to that authority.

### PCO-051 — Duplicate Active Pane Refusal (Slice 3, reserved)

Where the Pane Registry contract forbids duplicate live panes for
the same claim and role, the future validator MUST refuse duplicate
`active` records for that `(claim_ref, role)` pair while preserving
the ability to represent transitional or terminal history in later
record versions if separately ratified.

### PCO-052 — Optional Container Binding Match (Slice 3, reserved)

When `container_instance_id` or `container_instance_ref` is present,
the future validator MUST require the referenced Slice 2I-S / 2I-R
container-instance record to exist and to match the Pane Registry
record's `controller_id`, `lane_id`, and `claim_ref` context.
Non-container visible panes remain valid.

### PCO-053 — Pane Registry Strict Field Posture (Slice 3, reserved)

The future Pane Registry schema MUST reject unknown top-level fields
so terminal identity, claim binding, and optional container binding
remain auditable. The validator MUST tolerate orphaned `*.tmp.*`
files under the Pane Registry runtime directory by skipping them.

### PCO-054 — Slice 3 Boundary Statement (No Automation)

Slice 3 Pane Registry spec/protocol authoring defines visible-pane
identity records, lifecycle semantics, optional container-instance
binding semantics, and the future predicate range `PCO-046` through
`PCO-053`. It does NOT introduce schema files, examples, validator
code, tests, CLI commands, pane-spawn automation, Hermes runtime
hooks, runtime/provider/MCP/plugin configuration changes, Slice 4
Side-Effect Ledger behavior, Slice 5 `pco-fanin`, Slice 6
Integration Queue behavior, Slice 2I-R container runtime /
credential / egress / image work, or team-mode Features 007 / 008 /
009.

This statement is normative. It MUST appear in this spec, in the
companion architecture doc, and in
[`../../docs/operations/PANE_REGISTRY_PROTOCOL.md`](../../docs/operations/PANE_REGISTRY_PROTOCOL.md).

### PCO-055 — Side-Effect Ledger Record Schema (Slice 4, reserved)

The future tracked schema (provisionally
`schemas/side-effect-ledger.schema.yaml`) defines the Side-Effect
Ledger record contract: top-level `kind`
(`side-effect-ledger-record`), `record_type` (`side_effect`),
`schema_version` (`"1"`), `controller_id`, `lane_id`, `claim_ref`,
`effect_id`, `effect_kind`, `effect_status`, `occurred_at`,
`record_timestamp`, and `summary`. Optional fields include
`actor_role`, `pane_ref`, `pane_record_sha256`,
`active_work_ledger_ref`, `active_work_ledger_record_sha256`,
`completion_report_ref`, `completion_report_sha256`,
`integration_queue_ref`, `subject_ref`, `subject_sha256`,
`evidence_refs`, `redactions`, and `details`. The future
`side_effect_ledger_schema` validator check validates one record at
a time and cites
[`../../docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md`](../../docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md).

### PCO-056 — Side-Effect Ledger Requires Lane Binding (Slice 4, reserved)

Every Side-Effect Ledger record MUST bind to a discovered
Active-Work Ledger claim through `controller_id`, `lane_id`, and
`claim_ref`. The Side-Effect Ledger is evidence input for the lane;
it does not grant authority, replace the claim lifecycle, or replace
the Assignment Envelope.

### PCO-057 — Side-Effect Effect Id Scoped Uniqueness (Slice 4, reserved)

`effect_id` values MUST be unique within `(controller_id, lane_id,
YYYY-MM-DD)` when `occurred_at` can be resolved to a UTC day. This
preserves append-only event readability without requiring global ids.

### PCO-058 — Side-Effect Taxonomy and Status Enums (Slice 4, reserved)

The future schema MUST reserve stable taxonomy values for
`github_mutation`, `git_mutation`, `tracked_file_change`,
`external_tracker_mutation`, `runtime_process_action`,
`container_action`, `provider_mcp_plugin_config_change`,
`network_ci_deploy_action`, and
`credential_secret_adjacent_event`. Status values are `requested`,
`started`, `succeeded`, `failed`, `cancelled`, `observed`, and
`unknown`.

### PCO-059 — Side-Effect Evidence Redaction Posture (Slice 4, reserved)

Side-Effect Ledger records MUST NOT contain secrets, tokens, raw
credentials, provider API key material, private keys, session
cookies, unredacted private payloads, or logs that expose secret-
shaped strings. Records SHOULD use paths, hashes, opaque ids, URLs,
and redaction notes instead of copied payloads. Credential-adjacent
events may record non-secret scope and lifecycle metadata only.

### PCO-060 — Optional Pane Registry Binding Match (Slice 4, reserved)

When `pane_ref` or `pane_record_sha256` is present, the future
validator MUST require the referenced Pane Registry record to exist
when resolvable and to match the Side-Effect Ledger record's
`controller_id`, `lane_id`, and `claim_ref` context.

### PCO-061 — Optional Completion Report Binding Match (Slice 4, reserved)

When `completion_report_ref` is present and resolves to a local file,
the future validator MUST require `completion_report_sha256`, if
present, to match the referenced bytes. The binding is evidence
linkage only; Completion Reports remain the deterministic gate return
packet.

### PCO-062 — Future Integration Queue Binding Match (Slice 4, reserved)

When `integration_queue_ref` is present after Slice 6 exists, the
future validator MUST require the Integration Queue entry to match
the Side-Effect Ledger record's lane context. Before Slice 6 exists,
the field is reserved prose scope only.

### PCO-063 — Side-Effect Ledger Strict Field Posture (Slice 4, reserved)

The future Side-Effect Ledger schema MUST reject unknown top-level
fields so side-effect taxonomy, evidence references, and redaction
posture remain auditable. The validator MUST tolerate orphaned
`*.tmp.*` files under the Side-Effect Ledger runtime directory by
skipping them.

### PCO-064 — Slice 4 Boundary Statement (No Automation)

Slice 4 Side-Effect Ledger spec/protocol authoring defines
side-effect purpose, authoring authority, prose record shape,
taxonomy, redaction rules, linkage to Active-Work Ledger claims, Pane
Registry records, Completion Reports, future Integration Queue
entries, and the future predicate range `PCO-055` through `PCO-063`.
It does NOT introduce schema files, examples, validator code, tests,
CLI commands, runtime hooks, side-effect observation automation,
GitHub/CI/deploy/provider/MCP/plugin mutations, credential issuance,
secret capture, Slice 5 `pco-fanin`, Slice 6 Integration Queue
behavior, or team-mode Features 007 / 008 / 009.

This statement is normative. It MUST appear in this spec, in the
companion architecture doc, and in
[`../../docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md`](../../docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md).

### PCO-065 — Fan-In Evidence Packet Input Manifest (Slice 5, reserved)

The future fan-in evidence packet MUST include an input manifest that
binds every consumed Source-ratified envelope, tracked artifact,
Active-Work Ledger record, Worktree Lease record, Pane Registry
record, Completion Report, Side-Effect Ledger record, validator log,
and Git/GitHub evidence snapshot by path/URL/id and SHA256 when exact
bytes are available.

### PCO-066 — Candidate Integrated State Reconstruction (Slice 5, reserved)

Fan-in MUST reconstruct the candidate integrated state from tracked
artifacts and Git/ref evidence. It MUST NOT accept a lane statement
such as "complete", "safe", or "tests passed" as sufficient evidence
without the corresponding tracked artifact and validator-output
binding.

### PCO-067 — Validator Output Freshness (Slice 5, reserved)

Validator output is usable fan-in evidence only when the command,
tree/ref or candidate patch set, timestamp or run id, and output hash
are bound to the candidate integrated state. Stale validator output
MUST be classified separately from failing validator output.

### PCO-068 — Lane Authority Binding (Slice 5, reserved)

Every governed lane consumed by fan-in MUST bind to a Source-ratified
Assignment Envelope or prompt pointer and to a discovered Active-Work
Ledger claim. Inputs that lack that binding MAY be summarized as
advisory context, but they MUST NOT carry integration authority.

### PCO-069 — Completion Report Closure (Slice 5, reserved)

Every governed lane consumed by fan-in MUST have a Completion Report
or an explicit blocked/interrupted closure record. Missing closure
blocks any `ready_for_source_review` classification because the lane's
ratified gate has undefined return state.

### PCO-070 — Side-Effect Ledger Reconciliation (Slice 5, reserved)

Fan-in MUST reconcile externally observable effects against
Side-Effect Ledger records and cited evidence. Effects relevant to
integration that are absent, unresolved, or redaction-limited MUST be
classified explicitly and MUST NOT be treated as silently clean.

### PCO-071 — Cross-Lane Overlap Classification (Slice 5, reserved)

Fan-in MUST classify changed-path, ref, source-host, tracker, runtime,
provider/config, network/CI/deploy, and credential-adjacent overlaps
across lanes as `clean`, `expected_overlap`, `stale_artifact`,
`missing_evidence`, `conflict`, or `redaction_limited` before any
integration-readiness statement is emitted.

### PCO-072 — Lane Self-Report Exclusion (Slice 5, reserved)

Lane self-report is advisory evidence only. A fan-in verifier MUST
cross-check lane claims against tracked artifacts, validator output,
ledger records, Completion Reports, Side-Effect Ledger records, and
cited external evidence before treating the claim as verified.

### PCO-073 — Fan-In Redaction-Safe Evidence Posture (Slice 5, reserved)

Fan-in packets MUST NOT contain secrets, raw credentials, private
keys, session cookies, provider API key material, unredacted private
payloads, or logs that expose secret-shaped strings. Packets SHOULD
use paths, hashes, opaque ids, URLs, and redaction notes instead of
copied payloads.

### PCO-074 — Slice 5 Boundary Statement (No Automation)

Slice 5 `pco-fanin` spec/protocol authoring defines integration
verification under multi-lane authorship, the evidence inputs fan-in
must reconstruct, the prose fan-in evidence packet shape,
self-report-exclusion rules, side-effect reconciliation expectations,
conflict/drift classifications, serialized integration preservation,
and the future predicate range `PCO-065` through `PCO-073`. It does
NOT introduce schema files, examples, validator code, tests, CLI
commands, a `pco-fanin` executable, runtime hooks, side-effect
observation automation, GitHub/CI/deploy/provider/MCP/plugin
mutations, credential issuance, secret capture, Slice 6 Integration
Queue behavior, Source-ratification substitution, Phase 2 autonomy
expansion, or team-mode Features 007 / 008 / 009.

This statement is normative. It MUST appear in this spec, in the
companion architecture doc, and in
[`../../docs/operations/PCO_FANIN_PROTOCOL.md`](../../docs/operations/PCO_FANIN_PROTOCOL.md).

---

## Open Source Decisions (Slice 2.5 + 2R)

The following decisions are explicitly **unresolved** in this spec
authoring gate. They are policy choices Source must ratify before
the Slice 2.5 + 2R implementation gate begins. This spec records the
decision surface only; it does not invent policy.

### OSD-1 — Controller key custody mode (Slice 2.5)

Open question: how is the private signing key bound to a Controller?
Three candidate modes:

1. **Per-host key** — a private key generated locally on each
   workstation, never exported. A developer who drives two
   workstations holds two distinct Controller identities. Cheapest;
   matches the architect report §11 Slice 2.5 sketch.
2. **Per-developer tenant key** — a private key generated under a
   tenant root, optionally shared across the developer's
   workstations. A single developer is a single Controller identity
   across hosts. Heavier custody; required for cross-workstation
   team-mode work (Feature 009 in the architect report).
3. **Both, declaratively** — the controller-key record's
   `key_custody_mode` field declares which mode applies per record,
   and the validator enforces only that the declared mode is
   internally consistent. Most flexible; largest substrate surface.

This spec does **not** select one; it adds a required
`key_custody_mode` field to the controller-key schema (PCO-025) so
that whichever mode Source ratifies is recordable. Until Source
ratifies a mode, the Slice 2.5 implementation gate is blocked.

### OSD-2 — Controller-key record location

Open question: where do controller-key records live in the tree?
Candidate paths:

1. `tenants/<tenant>/controllers/<controller-id>.key.yaml` — sits
   beside existing tenant fixtures (Feature 001 dogfood pattern).
2. `governance/controller-keys/<controller-id>.key.yaml` — sits
   beside other governance-class records.
3. A per-workstation overlay path declared at deployment time —
   honors the Feature 001 "deployment-time overlay decisions"
   pattern for concrete bindings.

This spec does **not** select one. The Slice 2.5 implementation
gate is blocked on this decision because it determines which
mutation class the key record falls under (`identity` vs
`governance`) and therefore which ratification path applies.

### OSD-3 — Signature serialization shape

Open question: over what canonical byte form is the lease signature
computed, and in what encoding is the signature stored on the lease
record?

Recommendation deferred to schema-authoring time, but the decision
is load-bearing for `PCO-024` and must precede the Slice 2.5
implementation gate. The architect report does not pre-select.

### OSD-4 — `pco-allocate` pane-spawn handoff (Slice 2R)

Open question: does `pco-allocate` spawn the Architect/Implementer
pane directly after successful allocation, or does it stop after
allocation and leave pane spawn to a separate operator step?
Architect report §11 implies the latter (Slice 3 — Pane Registry —
is the slice that introduces pane-identity-bound spawning). This
spec defaults to the **separate spawn step** posture per `PCO-030`
but records the question as an open decision so Source can ratify
otherwise without re-opening the spec.

---

## Team-Mode Roadmap Note (Slice 2.5 + 2R Context)

Slice 2.5 + Slice 2R together are **local-solo-developer runtime
hardening** — they convert the existing read/validate/refuse
substrate (Slice 0, 0.5, 1/2, 2A) into a runtime that allocates
worktrees, signs leases, and refuses unsafe state mechanically on a
single developer's workstation. They do **not** introduce team-mode
operation across multiple developers or multiple workstations.

Per the architect report (`SUMMARY.md` and
`20260521T045722Z-architect-report.md` §§7, 13, 14) team-mode
operation requires three additional substrate layers, each separately
ratified after the Slice 2.5 + 2R gate:

1. **Project Coordination Ledger (PCL) — Feature 007 (TM-1)**: the
   team-mode equivalent of the Active-Work Ledger, tracked in the
   repository (not under `.hermes/`), naming the intent to work on a
   backlog item, the developer identity making the claim, the
   workstation identity, the Controller identity, the
   worktree+branch identifiers, and the lifecycle state.
2. **Distributed Identity Substrate — Feature 009**: developer
   identity + workstation identity + Controller identity binding,
   with per-tenant key custody policy that productionizes Slice
   2.5's per-host or per-tenant key into a multi-developer-aware
   model.
3. **Source-Host & Tracker Connectors — Feature 008**: governed
   mirrors for GitHub Issues / Jira / Linear. **Tracker and GitHub
   issues remain mirrors, not canonical authority, unless Source
   later ratifies a different team-mode design.** Mirror writes
   are side effects of PCL state transitions; mirror reads are
   used to detect drift; mirror entries MUST NOT advance a PCL
   state, ratify anything, or substitute for `BACKLOG.md`.

The Slice 2.5 + 2R spec authoring gate authorizes none of the above
workstreams. Their inclusion in the roadmap is a forward reference,
not an implementation promise.

---

## Out of Scope (Slice 0)

Slice 0 explicitly does NOT introduce:

* runtime enforcement of any kind (no multi-controller writing
  trials, no live coordination tooling);
* live conflict detection beyond the read-only
  `active_work_ledger_conflicts` pre-launch checks (semantic conflict
  analysis and runtime coordination remain later-slice concerns);
* automatic worktree allocation (Slice 2);
* visible-pane identity records (Slice 3);
* side-effect tracking (Slice 4);
* fan-in verification under multi-lane authorship (Slice 5);
* canonical-branch integration queueing (Slice 6);
* model, tool, CLI, account, runner, or QA-harness bindings (those
  remain deployment-time overlay decisions);
* replacement of Assignment Envelopes or handoffs as substantive
  authority;
* replacement of Source ratification.

---

## Deferral Rationale

Each later slice closes a specific Slice 0 non-goal and is deferred
for a specific reason:

| Slice | Closes | Deferred because |
|---|---|---|
| Slice 1/2 — Conflict / Pre-Launch Validator | worktree-path collisions across live claims; live lane uniqueness per controller; heartbeat and event claim-reference integrity; heartbeat monotonicity where timestamps are parseable; event-id uniqueness within `(controller_id, lane_id, YYYY-MM-DD)` | Landed as a validator-only layer above Slice 0 schema records; it refuses unsafe pre-launch state without allocating worktrees or launching panes. |
| Slice 2A — Worktree Lease substrate | intent-to-write primitive; cross-controller lease contention refusal before claim writes | Landed as a record/validate/refuse layer above Slice 1/2; runtime allocation deferred to Slice 2R; identity hardening deferred to Slice 2.5. |
| Slice 2.5 — Controller Identity Substrate | forgeable `controller_id` free-string risk that Slice 2A documents in §j; `worktree_lease_signature` (`PCO-024`) refusal of unsigned / mis-signed leases when key records exist | Paired with Slice 2R in the next ratified gate; productizing the allocator without identity hardening would ship an unauthenticated coordination protocol (architect report §11). |
| Slice 2R — Worktree Allocator Runtime | atomic `git worktree add` + lease + claim + event flow under lane lock; claim-writes-only-under-held-lease enforcement; pane launch gated by conflict validator; root checkout invariant preservation | Paired with Slice 2.5 in the next ratified gate; converts the Slice 1/2 + 2A paper refusal into runtime block. |
| Slice 3 — Pane Registry | visible-pane identity records | Pane identity is a privileged mutation class (Feature 001 FR-008-style) and requires its own ratified record contract. |
| Slice 4 — Side-Effect Ledger | externally observable side effects per lane | Prose/protocol boundary is authored; schema/examples/validator/tests/CLI/runtime observation and external mutations remain deferred. |
| Slice 5 — `pco-fanin` | integration verification under multi-lane authorship | Authored as prose/protocol in this gate; schema/examples/validator/CLI/runtime implementation is deferred. Fan-in cannot trust lane self-report; it depends on Slices 1–4 to reconstruct ground truth. |
| Slice 6 — Integration Queue | serialized canonical-branch landing order across lanes | Integration ordering depends on fan-in verification (Slice 5) and on Source-ratified gate definitions. |

The previously-planned Feature 005 dispatch / worktree / sandbox
runtime work is preserved as later-slice scope under PCO; the
substrate-before-automation discipline holds across all slices.

---

## Phase 1 / Phase 2 framing

Per Feature 002 FR-027 / FR-028, **Slice 0 is Phase 1**:
ratification-heavy, no autonomy expansion. The Slice 0 boundary
statement (PCO-011) is itself a Phase 1 constraint — until later
slices land *and* are independently ratified, multi-controller
execution remains a Phase 1 manual discipline.

**Slice 2.5 and Slice 2R are also Phase 1.** Per `PCO-032`, the
paired Slice 2.5 + 2R gate hardens local-solo-developer runtime
behavior; it does **not** authorize fully autonomous
multi-controller operation, does **not** authorize
cross-workstation operation, and does **not** ratify a team-mode
posture. The Phase 1 Source-ratified governance discipline
(privileged-class ratification per Feature 001 FR-008;
author/approver separation per FR-007; Source ratification per
Feature 002 FR-008/FR-016) is **preserved unchanged**: every Slice
2R runtime mutation continues to descend from a Source-ratified
Assignment Envelope; every Slice 2.5 controller-key record is an
identity-class mutation under Feature 001 FR-008; and every Slice
2R pane launch remains gated by the conflict validator (PCO-030).

No fully autonomous multi-controller or cross-workstation
operation is authorized by this spec authoring gate. Team-mode
operation (architect report §§7, 13) requires the separately
ratified Project Coordination Ledger (Feature 007), Distributed
Identity Substrate (Feature 009), and governed Source-Host /
Tracker Connectors (Feature 008).

---

## Acceptance Posture

A fresh-clone reviewer can verify the following from this spec
together with the prose protocol, the architecture doc, the schema,
and the validator check + tests:

1. The seven PCO slices and the Slice 0 boundary statement.
2. The Slice 0/1/2 functional requirements `PCO-001` through `PCO-018`.
3. The remaining non-goals and the slice each non-goal defers to.
4. The validator's `active_work_ledger_schema` check is registered
   and validates one record at a time against the schema.
5. The validator's `active_work_ledger_conflicts` check is registered,
   has focused CLI discoverability, and validates the pre-launch
   cross-record invariants without absorbing the schema check.
6. The unit tests at
   `validators/tests/unit/test_active_work_ledger_schema.py` and
   `validators/tests/unit/test_active_work_ledger_conflicts.py` cover
   the golden positive and negative cases.
7. The protocol's atomic-write rule (temp + fsync + rename) and
   advisory-lock rule (`flock(2)` on `locks/<lane-id>.lock`) are
   documented; runtime tooling that implements them is later-slice
   scope.
8. The relationship to Assignment Envelopes, handoffs,
   recommended-prompts, and one-driver-per-worktree is preserved
   without weakening any upstream contract.
9. The Slice 2.5 + 2R paired-gate posture: the Slice 2.5
   controller-key substrate (PCO-024, PCO-025, PCO-026) and the
   Slice 2R worktree allocator (PCO-027 through PCO-031) together
   convert read/validate/refuse paper substrate into runtime
   enforcement, with the boundary statement (PCO-032) preserving
   the substrate-before-automation discipline against later slices
   (3, 4, 5, 6, 0.5R) and against team-mode workstreams (Features
   007 / 008 / 009).
10. The Slice 2.5 + 2R Open Source Decisions surface (OSD-1 key
    custody, OSD-2 record location, OSD-3 signature serialization,
    OSD-4 pane-spawn handoff) is recorded; this spec authoring gate
    does NOT invent policy for any of them. The Slice 2.5 + 2R
    implementation gate is blocked on those decisions being
    Source-ratified.
11. The Team-Mode Roadmap Note: this paired slice is
    local-solo-developer runtime hardening; team-mode operation
    remains the separate Feature 007 / 008 / 009 workstream, and
    tracker / GitHub issues remain mirrors (never canonical
    authority) unless Source later ratifies a different design.
12. The Slice 3 Pane Registry spec/protocol posture: runtime records
    live under `.hermes/active-work-ledger/panes/`, future predicate
    codes reserve `PCO-046` through `PCO-053`, operator-visible
    compliance requires tmux identity, Pane Registry roles are
    distinct from Slice 2I-S container policy roles, and schema /
    examples / validator / CLI / tests / pane-spawn automation are
    deferred to a later gate.
13. The Slice 4 Side-Effect Ledger substrate posture: predicate
    codes reserve `PCO-055` through `PCO-063`, records are lane-bound
    evidence inputs for GitHub/git/tracker/runtime/container/provider/
    network/CI/deploy/credential-adjacent side effects, secret and
    private payload material is excluded, and runtime observation
    automation / external mutations are deferred to a later gate.
14. The Slice 5 `pco-fanin` spec/protocol posture: future predicate
    codes reserve `PCO-065` through `PCO-073`, fan-in reconstructs
    candidate integrated state from tracked artifacts, validator
    output, ledgers, reports, pane records, and side-effect records
    rather than lane self-report, and schema / examples / validator /
    CLI / runtime implementation / Integration Queue behavior are
    deferred to later gates.
