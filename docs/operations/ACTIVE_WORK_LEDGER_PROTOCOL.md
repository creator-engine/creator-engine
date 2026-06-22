# Active-Work Ledger Protocol

**Status**: Parallel Controller Orchestration (PCO) Slice 0 normative
protocol. Part of the **minimum repo-native delivery control plane**
and **not a Jira clone**. Layered onto, and subordinate to, the
Feature 001 governance substrate and the Feature 002 operating model.
A fresh clone is sufficient to apply this protocol; no external
tracker credential or network state is required.

## a. Purpose

When more than one Source-ratified Controller authors lanes of work
simultaneously — for example, when Hermes and a second Nefarious pane
both hold ratified envelopes pointing at different worktrees — the
one-driver-per-worktree rule from
[`../architecture/parallel-agent-development-model.md`](../architecture/parallel-agent-development-model.md)
is necessary but not sufficient. We additionally need a *coordination
substrate* that records, for any moment in time, **which Controller
is currently driving which lane**, and that lets a Controller verify
that fact before it launches a parallel Architect or Implementer
pane.

This protocol defines that substrate's static contract: the tracked
schema, the local runtime directory shape, the record fields, the
lease and stale-record semantics, the atomic-write and advisory-lock
rules, and the pre-launch read/validate behavior. **Slice 0 records
and validates these entries one record at a time. Slice 1/2 adds a
separate cross-record/pre-launch conflict validator for the minimal
claim/heartbeat/event invariants required before a Controller can
safely claim a lane/worktree.** Later slices still own worktree
allocation, pane registry, side-effect tracking, fan-in, integration
queueing, and live multi-controller writing.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 governance substrate | Author/approver separation; privileged-class enumeration; ratification flow. |
| Feature 002 operating model | Assignment-Envelope contract; verifies-not-ratifies; authority-conflict halt path. |
| [`../architecture/parallel-agent-development-model.md`](../architecture/parallel-agent-development-model.md) | One-driver-per-worktree rule; the parallel-pair shape. |
| [`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md) | Architectural companion to this protocol. |
| [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) | Controller / Implementer boundary policy. The ledger does not relax this boundary; every claim still operates under a ratified envelope. |
| [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md) | Pointer-only relay shape; ledger records cite envelopes and handoffs by path, never inline their content. |
| [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md) | Manifest count/hash preflight; ledger records are local-runtime and therefore not subject to manifest fidelity. |
| [`./ROOT_WORKTREE_INVARIANT.md`](./ROOT_WORKTREE_INVARIANT.md) | Navigation/orchestration-only invariant on the root checkout. |
| `schemas/active-work-ledger.schema.yaml` | Tracked machine-readable contract for ledger records. |

Where this protocol overlaps with the Feature 002 verifies-not-ratifies
invariant or with the Feature 001 author/approver separation contract,
the upstream contract controls. This protocol does not redefine those
contracts; it adds a coordination-substrate layer above them.

## c. Scope of Slice 0

Slice 0 is **record/validate only**:

* defines the tracked record schema;
* defines the local runtime directory shape;
* validates one record at a time against the schema;
* documents the lease, atomic-write, advisory-lock, and pre-launch
  read/validate disciplines that later slices will enforce.

Slice 1/2 now adds:

* `active_work_ledger_conflicts`, a separate cross-record validator
  layered above the schema check;
* live-claim collision detection for `worktree_path` under different
  `controller_id` values;
* live `controller_id`/`lane_id` uniqueness;
* heartbeat `claim_ref` and event `subject_claim_ref` resolution;
* heartbeat sequence monotonicity for parseable heartbeat timelines;
* event-id uniqueness within `(controller_id, lane_id, YYYY-MM-DD)`.

The split is intentional: `active_work_ledger_schema` remains the
Slice 0 one-record contract, while `active_work_ledger_conflicts`
implements the pre-launch refusal checks without allocating worktrees
or launching runtime automation.

Slice 0/1/2 still do **not**:

* enforce multi-controller execution;
* detect cross-lane semantic conflicts;
* allocate worktrees;
* bind any concrete tool / model / CLI / SaaS account / runner;
* replace Assignment Envelopes or handoffs as authority;
* replace Source ratification.

Slice 0 also does not cross-check claim/heartbeat/event records for
lane uniqueness, `worktree_path` collisions, heartbeat monotonicity,
event-log ordering, or stale-record reclamation. Those are the
explicit subjects of the later PCO slices listed in §t.

## d. Tracked-schema vs local runtime-state distinction

* `schemas/active-work-ledger.schema.yaml` is **tracked**. It is the
  canonical record contract, frozen at the commit level, and reviewed
  through the normal Source-ratified mutation flow.
* Ledger records (claim, heartbeat, event files) are **local runtime
  state**. They live under `.hermes/active-work-ledger/`, which is
  covered by the existing `.hermes/` ignore rule, and they MUST NOT
  be added to the index. Adding them would conflate runtime state
  with substrate.
* This protocol document, and the validator skeleton, are tracked.

## e. Runtime directory shape

The runtime directory layout is:

```
.hermes/active-work-ledger/
  claims/<controller-id>/<lane-id>.yaml
  heartbeats/<controller-id>/<lane-id>.yaml
  events/<YYYY>/<MM>/<DD>/<UTC-timestamp>-<controller-id>-<event-id>.yaml
  locks/<lane-id>.lock
```

* `claims/<controller-id>/<lane-id>.yaml` — one current claim record
  per `(controller, lane)` pair. Overwritten on lease renewal or
  release.
* `heartbeats/<controller-id>/<lane-id>.yaml` — the latest heartbeat
  record per `(controller, lane)` pair. Overwritten on each emission.
* `events/<YYYY>/<MM>/<DD>/<UTC-timestamp>-<controller-id>-<event-id>.yaml`
  — append-only event log entries. One file per event. Never edited,
  never deleted by the protocol itself; archival is a later-slice
  concern.
* `locks/<lane-id>.lock` — advisory `flock(2)` files. Empty file is
  fine; the file exists to give `flock` something to grip.

Orphaned atomic-write temporary files of the form
`<target>.tmp.<pid>.<nonce>` MAY appear under any of the above paths.
The validator MUST tolerate them by skipping (see §l).

## f. Controller id format

Pattern: `^[a-z][a-z0-9-]{2,63}$`.

Examples: `hermes-primary`, `nefarious-laptop-a`, `nefarious-laptop-b`.

A `controller_id` is **stable** per physical operator+host pair. It
MUST NOT embed:

* secrets, tokens, credentials, or installation ids;
* durable actor ids or app slugs;
* concrete model, tool, CLI, runner, or account identifiers.

Within a repo/project/profile scope, `controller_id` is the durable identity
that carries live Controller mutation authority. Duplicate live
mutation-capable Controller seats for the same `controller_id` are invalid:
there is one current writer authority for that identity until the seat becomes
terminal, transfers by a ratified handoff, or is re-entered by attach/resume.
Concrete process ids, tmux sessions, panes, sentinels, and harness sessions are
observational runtime evidence for this durable identity; they do not mint a
second ownership authority and do not supersede the ledger identity.

Concrete bindings remain deployment-time overlay decisions per
`docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md` §c precedent.

## g. Lane id format

Pattern: `^[a-z][a-z0-9-]{2,63}$`.

A `lane_id` is the coordination unit. The recommended convention is
`<feature-or-slice>-<short-suffix>` (e.g.,
`pco-slice0-active-work-ledger-author`). Lane ids are
human-meaningful but Slice 0 does not enforce structure beyond the
pattern.

### g.1 Identity and ownership interpretation for concurrent seats

Humans and Controllers interpret ledger ownership by exact record
identity, not by process, terminal, account, or natural-language lane
names:

* `controller_id` names the Controller seat that owns the live
  coordination records. It is stable per physical operator+host pair
  (§f) and is compared as an exact string. It is not a GitHub
  account, actor id, model id, tmux pane id, app slug, or signing-key
  alias.
* `lane_id` names the work lane inside the ledger. The live lane
  owner is the current live claim for the `(controller_id, lane_id)`
  pair, subject to the worktree collision rules in §s and the
  lease cross-reference in §w. A familiar or reused `lane_id` string
  is not enough to infer ownership without the matching
  `controller_id` and live claim record.
* `pane_label` is only a role hint on a ledger claim. Visible pane
  identity is recorded separately by the Pane Registry, which binds a
  pane to a claim through `controller_id`, `lane_id`, and `claim_ref`;
  terminal ids and pane ids are evidence for locating the pane, not
  authority to own the lane.
* `handoff_ref` and `subject_handoff_ref` are pointers to handoff
  documents. A handoff document does not itself transfer live ledger
  ownership. Operationally, ownership changes only when the outgoing
  claim is released or lapses and the receiving Controller records
  its own live claim under its own `controller_id` (and, when the
  lease layer is active, its own covering Worktree Lease).

This subsection clarifies human/operator interpretation only. It
does not add schema fields, change validation predicates, launch or
refuse runtime panes, migrate existing records, or close the broader
identity-hardening follow-ups.

## h. Claim record fields

A claim record (`record_type: claim`) carries:

* `kind: active-work-ledger-record` (discriminator).
* `record_type: claim`.
* `schema_version: "1"`.
* `controller_id` — per §f.
* `lane_id` — per §g.
* `record_timestamp` — ISO-8601 UTC `Z` or source-controlled reference.
* `worktree_path` — required; repo-relative or absolute path of the
  physical worktree the claim names. Treated as advisory, not a
  secret.
* `branch` — optional; branch name on which the claim operates.
* `envelope_ref` — required; repo-relative path to the active
  Assignment Envelope, or the literal `none` for coordination lanes
  that operate without an envelope.
* `handoff_ref` — optional; repo-relative path to the active handoff
  document.
* `recommended_prompt_ref` — optional; repo-relative path to the
  active recommended-prompt document.
* `lease_seconds` — required integer in `[60, 86400]`. Default is
  `3600` (one hour); the schema validates the range only.
* `claimed_at` — required timestamp at which the claim was created.
* `last_heartbeat_at` — required timestamp of the most recent
  heartbeat the Controller emitted for this claim. For fresh claims,
  equals `claimed_at`.
* `pane_label` — optional; one of `architect | implementer |
  controller | reviewer`. Generic role label only. NOT a model or
  tool binding.
* `released_at` — optional timestamp at which the claim was closed.
  When present, `release_reason` MUST also be present.
* `release_reason` — optional enum
  `{ completed, aborted, lapsed, handed_off }`; required iff
  `released_at` is present.

G2.002.1 adds four **optional, additive** operating-mode runtime-carrier
fields (available on any record kind; `schema_version: "4"` when carried).
They record posture only and mint no authority — the Assignment Envelope and
Operator ratification remain the substantive authority:

* `operating_mode` — optional; one of `strict | auto | transcendence`.
  Absent resolves to `strict`; migration never infers elevation.
* `autonomy_class` — optional; the G2.002.0 autonomy enum.
  `reserved_future_agent_ratification` is a placeholder and MUST NOT be an
  active carrier autonomy.
* `lane_kind` — optional; one of
  `read-only | implementation | review | approval | merge | audit`.
  Distinct from `pane_label`. Lets a downstream reviewer/approver/merger lane
  be a different lane kind from the implementer lane; G2.002.1 only carries the
  field — PR-review, approval, and merge enforcement are **downstream**.
* `ratification_evidence_ref` — optional inherited ratification-evidence
  pointer (path/reference string or structured mapping), required by the
  `operating_mode_runtime_carriers` validator for elevated modes
  (`auto`/`transcendence`) and privileged lane kinds (`approval`/`merge`).

Pre-v4 (`"1"`–`"3"`) records carry none of these and validate unchanged.

## i. Heartbeat record fields

A heartbeat record (`record_type: heartbeat`) carries:

* `kind`, `record_type: heartbeat`, `schema_version: "1"`,
  `controller_id`, `lane_id`, `record_timestamp` — shared envelope.
* `claim_ref` — required; repo-relative path to the claim file this
  heartbeat updates.
* `heartbeat_sequence` — required integer `>= 0`; monotonically
  non-decreasing per claim. Slice 0 validates type and lower-bound
  only; cross-record monotonicity is reserved for later slices.
* `emitted_at` — required timestamp at which the heartbeat was
  emitted.
* `note` — optional free-text status note, `maxLength: 1024`. MUST
  NOT contain secrets, tokens, credentials, or actor ids. Slice 0
  does not enforce this prohibition mechanically.

## j. Event log record fields

An event log record (`record_type: event`) carries:

* `kind`, `record_type: event`, `schema_version: "1"`,
  `controller_id`, `lane_id`, `record_timestamp` — shared envelope.
* `event_kind` — required enum:
  * `claim_created` — a new claim was written;
  * `claim_released` — a claim was closed cleanly (any
    `release_reason` other than `lapsed`);
  * `claim_lapsed` — a claim went stale and was treated as released;
  * `heartbeat_emitted` — a heartbeat was written;
  * `lane_handoff_announced` — the lane is being offered to another
    Controller;
  * `lane_handoff_received` — the lane has been received by the
    other Controller.
* `event_id` — required; matches pattern
  `^[a-z0-9][a-z0-9-]{2,63}$`. Stable within
  `(controller_id, lane_id, YYYY-MM-DD)` scope. Slice 0 does not
  enforce cross-record uniqueness.
* `event_timestamp` — required timestamp at which the event occurred.
* `subject_claim_ref` — optional repo-relative path to a claim file
  the event describes.
* `subject_handoff_ref` — optional repo-relative path to a handoff
  document the event references; used for `lane_handoff_*` events.
* `details` — optional structured object with `summary` and
  `actor_pane_label` fields. `unevaluatedProperties: false` —
  unknown keys are rejected.

## k. Lease / stale-record semantics

Every claim carries `lease_seconds`. The lease semantics are:

* Default `lease_seconds` is `3600`. Min `60`, max `86400`. The
  schema validates the range; the default is a prose convention.
* A claim is **live** when
  `now - last_heartbeat_at <= lease_seconds`.
* A claim is **stale** when
  `now - last_heartbeat_at > lease_seconds`.
* Stale records are **advisory** in Slice 0; Controllers SHOULD
  observe them but Slice 0 does not yet enforce reclamation.
* Later slices MAY reclaim a stale claim by emitting a `claim_lapsed`
  event, overwriting the heartbeat with a new sequence number, and
  taking the lane under a different `controller_id`. The reclamation
  flow itself is later-slice scope.

Slice 0 validates only that `lease_seconds` is an integer in
`[60, 86400]`; it does not validate any wall-clock relationship
between `claimed_at`, `last_heartbeat_at`, and `record_timestamp`.

## l. Atomic write approach

Writers MUST use the temp-file + fsync + rename pattern:

1. Write the new record to `<target>.tmp.<pid>.<nonce>` within the
   same directory as `<target>`.
2. `fsync(2)` the temp file.
3. `rename(2)` it over `<target>` atomically.

Writers MUST NOT partial-write into the live path. The validator
MUST tolerate the presence of orphaned `*.tmp.*` files by skipping
any path whose last name segment contains `".tmp."`; a stale temp
file is not a validation failure.

Slice 0 documents this discipline; runtime tooling that actually
performs the writes is a later-slice concern.

## m. Advisory lock approach

Around every read-modify-write sequence that touches a lane's claim
or heartbeat files, writers MUST hold an exclusive advisory lock on
`locks/<lane-id>.lock` using `flock(LOCK_EX)` (POSIX `flock(2)`).
The lock is advisory; cooperating writers respect it.

Slice 0 documents this discipline; the runtime tooling that takes
the lock is a later-slice concern.

## n. Event log shape

The event log is **append-only**. One event per file. The protocol
itself never edits or deletes event files. Each file's name carries
its own UTC timestamp, controller id, and event id so that ordering
is reconstructible from filenames.

`event_kind` is enumerated in §j. Later slices MAY introduce
additional event kinds via a schema-version bump; the Slice 0 set is
the floor.

### n.1 Slice 0.5 additive extension — completion-report event kinds

Slice 0.5 (Completion Report Substrate) additively extends this
schema with `schema_version: "2"` and four new `event_kind` values:

* `gate_opened` — a Source-ratified gate began under a recorded
  envelope + SHA256.
* `gate_closed` — a Source-ratified gate ended without a blocker
  (outcome `completed` or `partial`).
* `completion_report_emitted` — a schema-conforming Completion
  Report sidecar has been appended for this gate. The matching
  sidecar SHOULD be referenced via the new optional
  `details.completion_report_ref` pointer.
* `gate_blocked` — a Source-ratified gate was blocked or aborted;
  pairs with a class-F Completion Report sidecar.

The extension is **additive**: Slice 0 v1 records continue to
validate unchanged; v2 records simply expand the accepted
`event_kind` and `details` surface. The companion contract is
[`./COMPLETION_REPORT_PROTOCOL.md`](./COMPLETION_REPORT_PROTOCOL.md);
the tracked machine contract is
`schemas/completion-report.schema.yaml`.

### n.2 schema_version migration note

`schema_version` accepts `"1"` (Slice 0) and `"2"` (Slice 0.5).
Writers MAY emit either version. Readers that only understand v1
MUST ignore unknown `event_kind` values rather than treating them
as schema errors. There is no destructive migration; v1 → v2 is a
pure extension.

## o. Pre-launch claim read/validate behavior

Before a Controller starts a parallel Architect or Implementer pane,
it MUST:

1. Enumerate the live (non-stale) claims under
   `.hermes/active-work-ledger/claims/`.
2. Validate every read claim file against the schema using the
   `active_work_ledger_schema` validator check.
3. Refuse to claim a `worktree_path` already held by a live claim
   under a *different* `controller_id`. (Holding multiple live
   claims on the same worktree under the *same* controller is
   itself a one-driver-per-worktree violation handled by the
   controller boundary policy, not by this ledger.)
4. Write the new claim atomically (§l) under the lane's lock (§m).
5. Emit a `claim_created` event before transitioning the pane to
   active.

Slice 0 documents this discipline. The mechanical enforcement of
step (3) — the "refuse to claim" gate — is a later-slice concern
(the Slice 1 conflict validator).

## p. Slice 0 boundary statement

**Slice 0 records and validates Active-Work Ledger entries; it does
not yet enforce multi-controller execution, does not yet detect
cross-lane semantic conflicts, and does not yet allocate worktrees.
Enforcement is reserved for later PCO slices.**

This statement is normative. Reviewers MUST see it preserved
verbatim in this document and reflected in the schema description,
the architecture doc, and the feature spec.

## q. Relationship to Assignment Envelopes

Every claim record carries `envelope_ref` — a repo-relative path to
the Assignment Envelope under whose authority the lane operates, or
the literal `none` for coordination lanes that operate without an
envelope (e.g., architect-only planning).

The envelope, not the ledger, remains the substantive authority. A
claim record CANNOT grant the lane more authority than its envelope
grants. The ledger only records *which Controller is currently
holding the lane*; the envelope governs *what the lane is permitted
to author*.

## r. Relationship to handoff and recommended-prompt schemas

Claim records MAY cite a `handoff_ref` and a
`recommended_prompt_ref` when those documents exist. The ledger
never duplicates handoff or recommended-prompt content; it points to
those documents by repo-relative path. The pointer-only relay
discipline from
[`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md) applies.

The handoff and recommended-prompt schemas
(`schemas/handoff.schema.yaml`,
`schemas/recommended-prompt.schema.yaml`) remain the canonical
contracts for those documents. The ledger does not extend or
override them.

## s. Relationship to one-driver-per-worktree

The
[`parallel-agent-development-model.md`](../architecture/parallel-agent-development-model.md)
one-driver-per-worktree rule continues to apply. A claim names
exactly one physical `worktree_path` and exactly one driving
`controller_id`. Two live (non-stale) claims for the same
`worktree_path`, under *different* `controller_id` values, is a
collision that the Slice 1/2 `active_work_ledger_conflicts` validator
MUST reject before a Controller treats a lane/worktree as safely
claimable.

`active_work_ledger_schema` still does NOT cross-check this collision;
it validates one record at a time. The collision check is explicitly
owned by `active_work_ledger_conflicts` so the record-schema and
pre-launch-conflict responsibilities remain auditable as separate
layers.

## t. Relationship to future slices

Slice 0 introduced the schema and protocol primitives that later
PCO slices operate on. Slice 1/2 has now landed the conflict/pre-launch
validator layer:

* **Slice 1/2 — Conflict / pre-launch validator**: cross-record
  overlap detection, including the worktree-path collision described
  in §s, live lane uniqueness per controller, heartbeat-reference
  resolution, event claim-reference resolution, heartbeat monotonicity
  where timestamps are parseable, and event-id uniqueness within the
  `(controller_id, lane_id, YYYY-MM-DD)` scope.
* **Slice 2 — Worktree Allocator**: issues short-lived worktree
  leases that line up with ledger claims; resolves contention before
  a claim is written.
* **Slice 3 — Pane Registry**: visible-pane identity records (which
  Architect/Implementer pane is bound to which claim).
* **Slice 4 — Side-Effect Ledger**: tracks externally observable
  side effects per lane (CI runs, deploys, GitHub state mutations)
  so that fan-in verification has a structured input.
* **Slice 5 — `pco-fanin`**: integration verification under
  multi-lane authorship; explicitly does not trust lane self-report.
* **Slice 6 — Integration Queue**: serialized canonical-branch
  landing order across lanes.

Each slice keeps the substrate-before-automation discipline: protocol
and validator first, runtime tooling after.

## u. Prohibited surfaces

Ledger records MUST NOT carry:

* secrets, tokens, credentials, source-host installation ids;
* durable actor ids, app slugs, account names;
* concrete model, tool, CLI, runner, or QA-harness identifiers as
  normative upstream bindings;
* machine-local absolute paths beyond `worktree_path` (which is
  required and treated as advisory, not as a secret).

This prohibition mirrors the
`schemas/review-evidence.schema.yaml` and the controller-boundary
policy. Slice 0 does not enforce the prohibition mechanically beyond
the schema's structural constraints (`unevaluatedProperties: false`,
enum constraints on `pane_label` and `release_reason`); the broader
discipline is operational.

## v. Acceptance posture

A fresh-clone reviewer can verify the following from this document
alone:

1. What lives under `.hermes/active-work-ledger/` and why it is
   untracked.
2. What a claim record is, what a heartbeat record is, and what an
   event record is.
3. What `lease_seconds` and stale-record semantics mean in Slice 0
   (advisory).
4. The atomic-write rule (temp + fsync + rename) and the
   advisory-lock rule (`flock(2)` on `locks/<lane-id>.lock`).
5. The pre-launch read/validate discipline.
6. The Slice 0/1/2 boundary: one-record schema validation remains
   separate from read-only cross-record/pre-launch conflict checks; no
   worktree allocation or multi-controller runtime enforcement is
   introduced by this slice.
7. The relationships to Assignment Envelopes, handoffs,
   recommended-prompts, and one-driver-per-worktree.
8. The slice plan that closes each later-slice gap.

## w. Slice 2A — Worktree Lease cross-reference (additive)

Slice 2A introduces a sibling coordination primitive — the **Worktree
Lease** — that names a Controller's intent-to-write against a
physical worktree *before* a ledger claim is produced. The Worktree
Lease primitive lives in:

* tracked schema `schemas/worktree-lease.schema.yaml`;
* prose contract [`./WORKTREE_LEASE_PROTOCOL.md`](./WORKTREE_LEASE_PROTOCOL.md);
* runtime directory shape under
  `.hermes/active-work-ledger/leases/<controller-id>/<lease-id>.yaml`
  (still untracked; covered by the existing `.hermes/` ignore rule).

The Slice 2A validator surface extends `active_work_ledger_conflicts`
**additively**. The new predicates are:

* `claim_requires_live_lease` (`PCO-021`) — a live ledger claim
  whose `worktree_path` is not covered by a live worktree lease
  under the **same** `controller_id` is refused;
* `worktree_lease_conflict` (`PCO-022`) — two live worktree leases
  for the same normalized `worktree_path` under *different*
  `controller_id` values is refused;
* `worktree_lease_invalid_record` (`PCO-023`) — a structurally
  invalid lease record discovered during the conflict scan surfaces
  separately from `PCO-020`.

These predicates are **gated on the discovery of at least one valid
`worktree_lease` record** in the scanned tree. Trees that contain
zero lease records preserve Slice 1/2 behavior unchanged; this is
the Slice 2A backward-compatibility floor.

The Slice 1/2 worktree-collision predicate (`PCO-010`) remains in
force when leases are present: even with coverage, two live ledger
claims under different controllers on the same worktree still fail
`PCO-010`. The lease layer is an *additional* refusal surface, not
a replacement.

Slice 2A does **not** modify the Active-Work Ledger schema, does
**not** add tracked ledger records, and does **not** bump
`schemas/active-work-ledger.schema.yaml`'s `schema_version`. The
lease layer is a sibling primitive — not a child of `claims/`,
`heartbeats/`, or `events/`.

PCO-024 (Slice 2.5B) adds Ed25519 signature verification for
`schema_version: "2"` worktree-lease records via the
`worktree_lease_schema` check. Signature errors surface as `PCO-024`
and are separate from the structural `PCO-020` / `PCO-023` surface.
The `active_work_ledger_conflicts` predicates (`PCO-021` / `PCO-022`
/ `PCO-023`) operate on schema-valid leases regardless of signature
status; a signed lease with an invalid signature still participates
in conflict detection. See `docs/operations/WORKTREE_LEASE_PROTOCOL.md`
§j for the signature substrate specification.
