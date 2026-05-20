# Completion Report Protocol

**Status**: Parallel Controller Orchestration (PCO) Slice 0.5
normative protocol. Part of the **minimum repo-native delivery
control plane**. Layered onto, and subordinate to, the Feature 001
governance substrate, the Feature 002 operating model, and the PCO
Slice 0 Active-Work Ledger substrate. A fresh clone is sufficient to
apply this protocol; no external tracker credential or network state
is required.

Doctrinal predecessor:
`.hermes/research/parallel-pco-pr-root-reconciliation-20260520T040237Z/controller-completion-packet-protocol-investigation.md`.
That investigation named the gap this protocol now closes.

## a. Purpose

A **Completion Report** is the deterministic return packet emitted
by every Source-ratified gate. It is the substrate-level answer to
the question:

> Given that Source ratified an envelope and the gate has now ended,
> what did the gate return, what did it produce as evidence, and
> what is the exact next Source-ratifiable step (or the canonical
> reason no next step exists)?

Completion Reports translate prose terminal-packet discipline from
the Controller skills into a **machine-validatable contract** so
that, when later runtime hooks land, the runtime can refuse to
release a controller's final answer until a schema-conforming report
exists. This document is the static contract; the runtime hook
(Slice 0.5R) is a Hermes-side change ratified separately.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 governance substrate | Author/approver separation; privileged-class enumeration; ratification flow. |
| Feature 002 operating model | Assignment-Envelope contract; verifies-not-ratifies; authority-conflict halt path. |
| [`./ACTIVE_WORK_LEDGER_PROTOCOL.md`](./ACTIVE_WORK_LEDGER_PROTOCOL.md) | Sibling PCO Slice 0 substrate; Slice 0.5 binds completion-report events into the same ledger via additive event_kinds. |
| [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) | Controller / Implementer boundary; the report is a Controller-emitted artifact, not an Implementer-emitted one. |
| [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md) | Pointer-only relay shape; completion reports cite envelopes/handoffs by path+SHA256, never inline content. |
| [`../delivery/NEXT_TASK_PROTOCOL.md`](../delivery/NEXT_TASK_PROTOCOL.md) | §b ten-field post-merge rule; this protocol references it for class C-merge and does NOT duplicate it. |
| [`../delivery/DEFINITION_OF_DONE.md`](../delivery/DEFINITION_OF_DONE.md) | Cites this protocol for non-merge ratified gates. |
| `schemas/completion-report.schema.yaml` | Tracked machine-readable contract for completion-report artifacts. |
| `schemas/active-work-ledger.schema.yaml` | Slice 0.5 additively extends the event_kind enum used by this protocol. |

Where this protocol overlaps with upstream contracts, the upstream
controls. This protocol does not redefine those contracts; it adds
a return-packet layer above them.

## c. Scope of Slice 0.5

Slice 0.5 is **record/validate only**, mirroring PCO Slice 0's
substrate discipline:

* defines the tracked report schema (`schemas/completion-report.schema.yaml`);
* defines the trigger taxonomy (§d) and the canonical absence
  reasons (§i.3);
* defines the per-class Markdown and YAML templates and the
  well-formed/malformed example surface;
* registers two validator checks (CR-001, CR-002) and one warn-only
  check (CR-003);
* extends the Active-Work Ledger schema additively with four new
  event kinds so that future runtime tooling has a place to record
  gate transitions.

Slice 0.5 does **not**:

* implement any Hermes runtime hook (deferred to Slice 0.5R);
* automatically detect ratified envelopes that lack a paired
  completion-report artifact under runtime conditions (CR-002
  applies CI-time, against tracked examples and any tracked envelope
  pointers);
* retroactively close dangling gates from before this slice
  activates (deferred to Slice 0.5T grandfather-exemption);
* re-prose the existing ten-field merge rule (§b of
  `NEXT_TASK_PROTOCOL.md` controls for class C-merge);
* bind any concrete tool, model, CLI, runner, account, or
  source-host identifier as authority.

## d. Trigger taxonomy

The discriminator is the presence of a Source-ratified envelope or
prompt pointer with a verified SHA at the moment the gate opens. If
there is no such pointer, the activity is advisory; if there is, the
activity is a governed syscall and the completion report is its
return packet.

### d.1 Classes that MUST emit a completion report

| Class | Name | Discriminator | Notes |
|---|---|---|---|
| **A** | Source-ratified saved prompt execution (universal case) | Envelope/prompt file exists at a pinned path; Source emitted a ratification line citing its SHA256. Also covers the visible architect/engineer pane subclass — a pane was launched by a Controller against a ratified handoff/prompt SHA. | The universal case. All other report-required classes also satisfy A. |
| **C-merge** | Git/GitHub mutation gate that ended at a canonical-branch merge | Mutation class includes any `repo-mechanics`, `governance`, `identity`, `security`, `attestation`, `redaction`, `deploy`, or `release` work that closed at a merge commit. | Carries the ten `NEXT_TASK_PROTOCOL.md` §b fields via a structured `merge_report` object. This protocol does NOT duplicate the prose ten-field rule; it cites it. |
| **C-pr-only** | Git/GitHub mutation gate without a merge | A Source-ratified PR open / edit / review / close gate that did not produce a merge commit. | Carries `pr_action` and `pr_identifiers`; no `merge_report`. |
| **D** | Non-Git runtime / config / provider / credential / tooling mutation gate | Mutation lands in environment, provider account, secret store, MCP config, Hermes profile, tmux session, or external service. | Repo validators cannot see this directly. Report MUST cite either a Side-Effect Ledger record (Feature 005 Slice 4/7 surface) OR an interim side-effect note path + SHA256 pinned under `.hermes/`. |
| **E** | Read-only research gate that consumed a ratified prompt | A ratified prompt opened a research lane; outputs are evidence artifacts. | Report MUST cite the research archive path, the evidence index path, and at least one `evidence_artifact_pointers` entry. |
| **F** | Blocked / interrupted gate after ratification | Gate opened, then aborted, paused, or escalated without completing. | Report MUST set `outcome` to `blocked` or `aborted`, name the blocker, and supply a resumption pointer (or an explicit "no resumption planned" rationale). A blocked gate without a closure report is undefined runtime state. |

### d.2 Classes that MUST NOT emit a completion report

| Class | Name | Discriminator | Notes |
|---|---|---|---|
| **G** | Simple Source question / advisory answer without an approved gate | No envelope file, no SHA, no ratification line. | The presence of "Source ratifies" text in chat without a pinned prompt file is NOT a ratified gate. |
| **H** | Exploratory local inspection without a ratified mutation/run envelope | Controller looks around (read-only, no envelope, no SHA, no claim record in the Active-Work Ledger). | If the Controller writes to the ledger or substantively authors `.hermes/` artifacts, the activity has graduated and the rule re-evaluates. |

### d.3 Discriminator rule (machine-applicable)

A completion report is required **if and only if** at least one of
the following is true at the time of final-answer emission:

1. The current Active-Work Ledger contains an open `claim` record
   (status not `released`/`lapsed`) whose `envelope_ref` is
   non-empty and whose `envelope_sha256` is recorded; OR
2. A Source-ratified prompt file exists under a pinned path and its
   SHA256 was acknowledged in this controller session; OR
3. The session opened a `gate_opened` event record (Slice 0.5
   additive event_kind) that has not yet been paired with a
   `gate_closed` / `completion_report_emitted` event.

If none of (1)–(3) hold, the session is class G or H and no
completion report is required.

## e. Artifact location and naming

* **Markdown body**: the human surface. Lives under
  `.hermes/research/<run-archive>/completion-report-<timestamp>.md`
  for classes A, C-merge, C-pr-only, and E, or under
  `.hermes/completion-reports/<lane_id>/<timestamp>.md` for classes
  D and F.
* **YAML sidecar**: the machine surface. Same basename, `.yaml`
  extension, same directory.
* The validator validates the YAML sidecar; the runtime hook
  (Slice 0.5R) and the warn-only CR-003 check validate that the
  Markdown body contains the three required terminal section
  headers.
* Timestamps use ISO-8601 compact form
  (`YYYYMMDDThhmmssZ`) in filenames.
* All paths under `.hermes/` remain local-ignored; only the schema,
  the prose protocol, the templates, the validator, and the
  well-formed/malformed examples are tracked.

## f. Universal required fields

Every completion-report sidecar MUST carry the following fields
(full schema definition: `schemas/completion-report.schema.yaml`):

| Field | Purpose |
|---|---|
| `kind: completion-report` | Discriminator constant. |
| `schema_version: "1"` | Slice 0.5 ships v1. |
| `gate_class` | One of `A`, `C-merge`, `C-pr-only`, `D`, `E`, `F`. |
| `envelope_ref` | Repo-relative path to the Source-ratified envelope/prompt file. |
| `envelope_sha256` | 64 lower-hex SHA256 of the envelope file. |
| `controller_id`, `lane_id` | Same patterns as `active-work-ledger.schema.yaml`. |
| `gate_opened_at`, `gate_closed_at` | Same timestamp shape as `active-work-ledger.schema.yaml` `record_timestamp`. |
| `outcome` | One of `completed`, `partial`, `blocked`, `aborted`. Class F maps to `blocked` or `aborted`; other classes use `completed` or `partial`. |
| `summary` | Short prose summary (1–4096 chars). Maps to the `Summary` terminal section. |
| `recommended_immediate_next_step` | Object with `description`, `rationale`, `next_action_kind`. Maps to the `Recommended immediate next step` terminal section. |
| `exact_next_source_prompt` | Object with `kind` (`present` or `none`) and the required siblings. Maps to the `Exact next Source prompt pointer+SHA256` terminal section. |
| `terminal_packet_sections_present` | Self-declared booleans for each of the three terminal section headers; cross-verified by the runtime hook and CR-003. |
| `evidence_artifact_pointers` | Required for class E (at least one entry); optional for other classes. |

## g. Class-specific required fields

| Class | Class-specific required fields | Notes |
|---|---|---|
| **A** | (none beyond universal) | `evidence_artifact_pointers` is optional but recommended. |
| **C-merge** | `merge_report` (object encoding the ten `NEXT_TASK_PROTOCOL.md` §b fields). | The structured object records the same facts as the prose ten-field rule; the prose rule continues to control. |
| **C-pr-only** | `pr_action`, `pr_identifiers`. | No `merge_report`. |
| **D** | `mutation_descriptors` (array), AND either `side_effect_ledger_ref` OR (`interim_side_effect_note_ref` + `interim_side_effect_note_sha256`). | Identifiers MUST be redacted per the well-formed handoff examples precedent. |
| **E** | `research_archive_path`, `evidence_index_path`, at least one `evidence_artifact_pointers` entry. | `outcome` MAY be `completed` even when `exact_next_source_prompt.kind == none`. |
| **F** | `blocker_description`, `resumption_pointer` (`kind: present` with pointer+SHA, or `kind: none` with rationale). | `outcome` MUST be `blocked` or `aborted`. |

## h. Terminal-packet section discipline

Every completion-report Markdown body MUST contain three literal
section headers in this exact canonical order:

1. `Summary`
2. `Recommended immediate next step`
3. `Exact next Source prompt pointer+SHA256`

These three headers are the cross-skill terminal packet shape the
Controller continuity / GitHub-PR workflow skills already require.
This protocol encodes that shape so:

* CR-001 fails when the schema fields backing those sections are
  missing or malformed;
* CR-003 (warn-only in v1) fails when the Markdown body is present
  but does not embed the three headers in canonical order;
* the Slice 0.5R runtime hook will refuse to release the terminal
  answer when the headers are missing from the live text.

Each Markdown template under `templates/hermes/completion-reports/`
embeds the headers in canonical order. Authoring a new report MUST
copy the template, fill the placeholders, and never reorder or
rename the headers.

## i. Recommended-next-step shape

### i.1 Required fields

`recommended_immediate_next_step` is an object with:

* `description` — what the next action is (1–2048 chars);
* `rationale` — why this action follows from the just-completed gate
  (1–2048 chars);
* `next_action_kind` — one of:
  * `source_ratifiable_prompt` — there is a concrete next prompt and
    `exact_next_source_prompt.kind == present`;
  * `backlog_refresh_and_source_escalation` — covers
    `NEXT_TASK_PROTOCOL.md` §c.3 (ambiguous / stale state needing
    Source attention);
  * `blocker_resolution` — covers §c.4 (blocked gate needing a
    narrow blocker-resolution prompt);
  * `no_next_gate` — the only value permitted when
    `exact_next_source_prompt.kind == none`.

### i.2 `exact_next_source_prompt` shape

When `kind == present`:

* `prompt_path` — repo-relative pointer (or `.hermes/`-relative
  pointer for unratified-yet drafts; the validator accepts the
  filename pattern, not the on-disk presence);
* `prompt_sha256` — 64 lower-hex SHA256;
* `canonical_ratification_line` — the line Source uses to authorise
  the next gate. Wording is set by the existing skill doctrine; the
  schema enforces presence, not specific text.

When `kind == none`:

* `none_rationale` — MUST cite exactly one of the canonical absence
  reasons (§i.3). Improvised "no next step" without a cited reason
  MUST fail validation.

### i.3 Canonical absence reasons

| Rationale | Meaning |
|---|---|
| `roadmap_milestone_complete` | The last gate of a roadmap milestone closed; the next milestone has not opened. |
| `source_paused_program` | Source explicitly paused; no next gate is scheduled. |
| `awaiting_external_dependency` | A non-controller dependency (CI, deploy, upstream merge, external review) has not landed. |
| `backlog_refresh_required` | The backlog needs Source curation before any next gate can be selected; covers `NEXT_TASK_PROTOCOL.md` §c.3. |

## j. Active-Work Ledger event integration

Slice 0.5 additively extends
`schemas/active-work-ledger.schema.yaml` with `schema_version: "2"`
and four new `event_kind` values. The semantics are:

| event_kind | Emitted when | Required pairing |
|---|---|---|
| `gate_opened` | A Source-ratified gate begins (envelope+SHA recorded). | Pairs with a later `gate_closed` or `gate_blocked`. |
| `gate_closed` | A Source-ratified gate ends without a blocker. | Pairs with a `completion_report_emitted` whose report has `outcome ∈ {completed, partial}`. |
| `completion_report_emitted` | A schema-validated completion-report sidecar has been appended for this gate. | `details.completion_report_ref` points at the report. |
| `gate_blocked` | A Source-ratified gate was blocked or aborted. | Pairs with a class-F report; `details.completion_report_ref` SHOULD point at it. |

Older v1 readers ignore unknown event kinds; v2 readers accept the
extended set. The extension is additive; v1 ledger records continue
to validate.

## k. Tracked-substrate vs local runtime-state distinction

* `schemas/completion-report.schema.yaml`, the templates under
  `templates/hermes/completion-reports/`, the well-formed/malformed
  examples under `examples/well-formed/completion-reports/` and
  `examples/malformed/completion-reports/`, and the validator
  registrations under
  `validators/creator_engine_validator/checks/` are **tracked**.
* Completion-report artifacts live under `.hermes/` and are **not
  tracked**. The validator validates one artifact at a time when run
  against a path; the CI surface validates the tracked examples.
* The Slice 0.5R runtime hook will read the local artifacts; it is
  Hermes-side and ships separately.

## l. Validator checks

| Check | FR | Scope |
|---|---|---|
| `completion_report_schema` | CR-001 | Validates one completion-report YAML sidecar at a time against the schema. |
| `completion_report_required_for_envelope` | CR-002 | For every Source-ratified envelope/prompt file present in the scanned paths, verifies that exactly one schema-conforming completion-report sidecar exists pointing back at that envelope's recorded SHA256. |
| `completion_report_terminal_sections` | CR-003 (warn) | When a completion-report Markdown body is present, verifies it contains the three required terminal section headers in canonical order. Emits warnings, not errors, in v1. |

Failures cite the relevant FR and reference this protocol document
at `docs/operations/COMPLETION_REPORT_PROTOCOL.md`.

## m. Mutation classes and prohibited surfaces

Completion-report artifacts MUST NOT carry:

* secrets, tokens, credentials, source-host installation ids;
* durable actor ids, app slugs, account names;
* concrete model, tool, CLI, runner, or QA-harness identifiers as
  normative upstream bindings;
* machine-local absolute paths beyond the advisory `worktree_path`
  inherited from the Active-Work Ledger discipline.

For class D reports, `mutation_descriptors[].target_identifier_redacted`
MUST be a redacted reference (e.g., `mcp.config:<redacted>`,
`provider:<redacted>`), never the raw identifier.

## n. Slice 0.5 boundary statement

**Slice 0.5 records and validates completion-report artifacts; it
does NOT yet implement the Hermes final-answer / send-blocking
runtime hook, does NOT yet retroactively close dangling gates, and
does NOT yet implement the governed-override emergency bypass.
Enforcement vectors are reserved for later slices (Slice 0.5R
runtime hook; Slice 0.5T backfill; Slice 0.5G governed override).**

This statement is normative. Reviewers MUST see it preserved
verbatim in this document and reflected in the schema description
and the feature spec.

## o. Relationship to future slices

| Slice | Closes | Deferred because |
|---|---|---|
| Slice 0.5R — Hermes runtime hook | Final-answer / send-blocking enforcement of CR-001 / CR-002 / CR-003 in Hermes. | The substrate must land before the runtime hook can read it. |
| Slice 0.5T — Backfill / dangling-gate protocol | Historical gates without completion reports. | Requires a Source-ratified grandfather-exemption that depends on the substrate being canonical. |
| Slice 0.5G — Governed-override emergency bypass | Optional Source-ratified one-shot bypass for legitimate emergencies. | Deferred until a real instance arises. |
| Feature 005 Slice 4 / 7 — Side-Effect Ledger | Replaces the interim side-effect note pointer for class D reports. | Side-effect ledger is its own substrate; interim pointer is a placeholder. |

## p. Acceptance posture

A fresh-clone reviewer can verify the following from this document
alone:

1. The completion-report contract has a tracked YAML schema, a
   tracked prose protocol, six per-class templates (Markdown + YAML),
   and well-formed / malformed examples.
2. The trigger taxonomy distinguishes classes that MUST emit a
   report (A, C-merge, C-pr-only, D, E, F) from classes that MUST
   NOT (G, H).
3. The three literal terminal section headers
   (`Summary`, `Recommended immediate next step`,
   `Exact next Source prompt pointer+SHA256`) appear verbatim and
   in canonical order in every template.
4. CR-001, CR-002, and CR-003 are registered; CR-001 and CR-002
   fail CI on malformed examples and pass on well-formed examples.
5. The Active-Work Ledger schema additively accepts
   `schema_version: "2"` and the four new event kinds.
6. The Slice 0.5 boundary statement (§n) is preserved.
7. The runtime hook is explicitly deferred to Slice 0.5R; no
   runtime code lands in this slice.
