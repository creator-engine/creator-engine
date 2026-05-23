# Side-Effect Ledger Protocol

**Slice**: PCO Slice 4 (Side-Effect Ledger)
**Status**: Spec/protocol authored only. Schema, examples,
validator, CLI discoverability, tests, runtime hooks, and observation
automation are deferred to a later gate.
**Architectural companion**:
[`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md)

---

## 1. Purpose

The Side-Effect Ledger records externally observable effects produced
while a PCO lane is active. It gives later fan-in verification a
redaction-safe index of actions that may have changed repository
state, source-host state, tracker state, runtime/process state, CI
state, deployment state, provider configuration, or credential-adjacent
surfaces.

A Side-Effect Ledger record is a structured statement that a lane
caused, observed, requested, or verified one side effect. The record
does not grant authority and does not replace the artifact it points
to. Assignment Envelopes remain the authority for work; Active-Work
Ledger claims remain the authority for lane lifecycle; Worktree Lease
records remain the authority for worktree contention; Pane Registry
records remain the authority for visible-pane identity; Completion
Reports remain the deterministic return packet for a gate.

## 2. Authorship and Lane Relationship

Only actors operating under a Source-ratified lane may author
Side-Effect Ledger records:

- a Controller MAY author records for side effects it directly
  performs or observes while verifying the lane;
- an Architect, Implementer, Reviewer, or Verification pane MAY author
  records for side effects within its assigned lane authority;
- a Controller MAY relay a pane-authored record by pointer, but the
  record MUST still name the originating lane and actor role.

Each record MUST bind to the PCO lane context: `controller_id`,
`lane_id`, `claim_ref`, and an optional `pane_ref` when a Pane
Registry record exists. Side-effect records are lane-scoped evidence
inputs for later fan-in; they are not self-ratification, not reviewer
approval, and not merge permission.

## 3. Prose Record Shape

The future Side-Effect Ledger schema is expected to use a strict
top-level record shape. This gate defines the prose contract only.

Required fields:

| Field | Purpose |
|---|---|
| `kind` | Required discriminator, provisionally `side-effect-ledger-record`. |
| `record_type` | Required discriminator, provisionally `side_effect`. |
| `schema_version` | Required version string, initially `"1"` in the future schema gate. |
| `controller_id` | Controller id matching the Active-Work Ledger format and redaction caveats. |
| `lane_id` | Lane id matching the Active-Work Ledger format. |
| `claim_ref` | Pointer to the Active-Work Ledger claim active when the effect occurred. |
| `effect_id` | Stable non-secret id unique within `(controller_id, lane_id, UTC day)`. |
| `effect_kind` | Taxonomy value from §4. |
| `effect_status` | One of `requested`, `started`, `succeeded`, `failed`, `cancelled`, `observed`, or `unknown`. |
| `occurred_at` | ISO-8601 UTC timestamp, or a source-controlled reference when a comparable timestamp is unavailable. |
| `record_timestamp` | Timestamp for the record write. |
| `summary` | Short redaction-safe human summary. |

Optional fields:

| Field | Purpose |
|---|---|
| `actor_role` | One of `controller`, `architect`, `implementer`, `reviewer`, or `verification`. |
| `pane_ref` | Pointer to a Pane Registry record, when present. |
| `pane_record_sha256` | SHA256 of the Pane Registry record observed by the writer. |
| `active_work_ledger_ref` | Pointer to the related claim, heartbeat, or event record when distinct from `claim_ref`. |
| `active_work_ledger_record_sha256` | SHA256 of the related Active-Work Ledger record. |
| `completion_report_ref` | Pointer to the gate Completion Report that summarizes this side effect. |
| `completion_report_sha256` | SHA256 of the referenced Completion Report sidecar. |
| `integration_queue_ref` | Future pointer to the Integration Queue entry that consumes the record. |
| `subject_ref` | Redaction-safe pointer to the affected object, such as a PR URL, commit SHA, workflow-run id, deployment id, tracker item id, process id reference, container-instance id, or provider/config record pointer. |
| `subject_sha256` | SHA256 of a local evidence file or exported metadata snapshot. |
| `evidence_refs` | Redaction-safe list of paths, URLs, ids, hashes, or log excerpts approved for inclusion. |
| `redactions` | List of redaction notes explaining omitted secret, credential, or private payload material without revealing it. |
| `details` | Small structured object for non-secret metadata; must not contain raw private payloads. |

Timestamp fields SHOULD use UTC `Z` form when the writer has a
reliable clock. Hash fields are SHA256 over the exact referenced bytes
when those bytes are available locally. References SHOULD be paths,
object ids, run ids, URLs, or hashes rather than copied payloads.

## 4. Side-Effect Taxonomy

Future schema/validator work MUST reserve stable taxonomy values for:

- `github_mutation`: PR, issue, label, reviewer, branch-protection,
  release, environment, or repository-setting mutation on GitHub.
- `git_mutation`: local commit, tag, branch, worktree, ref update, or
  remote push/fetch/pull side effect.
- `tracked_file_change`: tracked filesystem content created, modified,
  deleted, staged, or committed within the lane's worktree.
- `external_tracker_mutation`: Jira, Linear, GitHub Issue mirror, or
  other tracker/document mutation.
- `runtime_process_action`: process, shell session, long-running
  command, tmux, worker, or host runtime action.
- `container_action`: container image, container instance, network
  policy, mount, artifact collection, or garbage-collection action.
- `provider_mcp_plugin_config_change`: model-provider, MCP, plugin, or
  local configuration change.
- `network_ci_deploy_action`: CI run, network call, deployment,
  environment, release, or remote execution action.
- `credential_secret_adjacent_event`: credential issuance, use,
  revocation, scope grant, or secret-adjacent observation where only
  redaction-safe metadata may be recorded.

Taxonomy values identify the side-effect surface, not whether the
effect was authorized. Authority still comes from the Assignment
Envelope and the upstream governance substrate.

## 5. Privacy, Security, and Redaction

Side-Effect Ledger records MUST NOT contain:

- secrets, tokens, raw credentials, private keys, or session cookies;
- provider API key material, model-provider credential material, or
  credential broker token values;
- raw private request or response payloads unless separately ratified
  for disclosure;
- unredacted logs that include private payloads, customer data, or
  secret-shaped strings;
- durable account ids, model identifiers, or installation ids where a
  redaction-safe alias or pointer is sufficient.

Records SHOULD use hashes, paths, opaque ids, and redaction notes
instead of copying evidence bodies. A credential-adjacent event may
record that a scoped credential was issued, used, or revoked, but it
MUST record only the non-secret scope, issuer reference, expiration,
and evidence pointer.

## 6. Linkage to PCO Artifacts

Each record MUST be traceable to the lane substrate:

- Active-Work Ledger: `claim_ref` is required; related event or
  heartbeat pointers may appear when relevant.
- Pane Registry: `pane_ref` may identify the visible pane that caused
  or observed the effect.
- Completion Report: `completion_report_ref` may bind the effect into
  the gate return packet.
- Integration Queue: `integration_queue_ref` is reserved for Slice 6 so
  future landing-order decisions can cite the side-effect inventory.

Later `pco-fanin` verification MUST treat the ledger as an evidence
index, not as trusted self-report. Fan-in reconstructs integrated
state from tracked artifacts, validator output, and referenced
evidence.

## 7. Predicate Reservation

The future schema/examples/validator gate reserves the next additive
PCO codes after the Pane Registry substrate (`PCO-046` through
`PCO-053`) and its boundary statement (`PCO-054`):

| Code | Future check |
|---|---|
| `PCO-055` | Side-Effect Ledger record schema. |
| `PCO-056` | Required lane binding to Active-Work Ledger claim. |
| `PCO-057` | Effect id scoped uniqueness within `(controller_id, lane_id, UTC day)`. |
| `PCO-058` | Effect kind and status enum validity. |
| `PCO-059` | Redaction-safe evidence reference posture. |
| `PCO-060` | Optional Pane Registry binding exists and matches claim context. |
| `PCO-061` | Optional Completion Report binding exists and is hash-consistent when resolvable. |
| `PCO-062` | Future Integration Queue binding exists and matches lane context when present. |
| `PCO-063` | Unknown field refusal / strict schema posture and `*.tmp.*` skip behavior. |

If live `main` later reserves any of these codes before the
implementation gate, the implementation gate MUST choose the next
free additive range and update this protocol before landing code.

## 8. Explicit Non-Goals

Slice 4 spec/protocol authoring does NOT introduce:

- schema files, examples, fixtures, validator code, tests, or CLI
  commands;
- runtime hooks or automation for observing side effects;
- GitHub, git, tracker, CI, deploy, provider, MCP, plugin, credential,
  container, network, or runtime mutations;
- fan-in implementation or Integration Queue implementation;
- pane-spawn automation or Side-Effect Ledger writer automation;
- any authority to expose secrets, tokens, credentials, or private
  payloads.

## 9. Slice 4 Boundary Statement

**Slice 4 Side-Effect Ledger spec/protocol authoring defines
side-effect purpose, authoring authority, prose record shape,
taxonomy, redaction rules, linkage to Active-Work Ledger claims, Pane
Registry records, Completion Reports, future Integration Queue
entries, and the future predicate range `PCO-055` through `PCO-063`.
It does NOT introduce schema files, examples, validator code, tests,
CLI commands, runtime hooks, side-effect observation automation,
GitHub/CI/deploy/provider/MCP/plugin mutations, credential issuance,
secret capture, Slice 5 `pco-fanin`, Slice 6 Integration Queue
behavior, or team-mode Features 007 / 008 / 009.**

## 10. Future Evidence

The future schema/examples/validator gate MUST provide:

- `--list-checks` discoverability for the Side-Effect Ledger check(s);
- focused Side-Effect Ledger scan command discoverability;
- well-formed and malformed examples for each taxonomy family;
- stable PCO-code failures for missing required fields, invalid ids,
  invalid taxonomy/status values, unresolved claim binding, invalid
  optional pane/report/queue binding, unsafe evidence payloads,
  unknown fields, and orphaned `*.tmp.*` skip behavior;
- tests proving read-only behavior and composition with Active-Work
  Ledger, Pane Registry, Completion Reports, and future Integration
  Queue entries.
