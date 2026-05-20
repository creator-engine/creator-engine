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

### PCO-018 — Slice 1/2 Validator Discoverability

The validator registry and CLI MUST expose the Slice 1/2 check as
`active_work_ledger_conflicts`, while preserving
`active_work_ledger_schema` as the one-record Slice 0 schema check.
A focused CLI path such as
`creator_engine_validator scan-active-work-ledger-conflicts <path>` MAY
run the pre-launch layer alone.

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
| Slice 2 — Worktree Allocator | automatic worktree allocation | Allocation requires a ratified conflict/pre-launch validator on which to base lease decisions. |
| Slice 3 — Pane Registry | visible-pane identity records | Pane identity is a privileged mutation class (Feature 001 FR-008-style) and requires its own ratified record contract. |
| Slice 4 — Side-Effect Ledger | externally observable side effects per lane | Side-effect tracking depends on a stable lane substrate (Slice 0) and on conflict/pre-launch validation (Slice 1/2). |
| Slice 5 — `pco-fanin` | integration verification under multi-lane authorship | Fan-in cannot trust lane self-report; it depends on Slices 1–4 to reconstruct ground truth. |
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
