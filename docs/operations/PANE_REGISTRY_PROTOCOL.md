# Pane Registry Protocol

**Slice**: PCO Slice 3 (Pane Registry)
**Status**: Spec/protocol authored only. Schema, examples, validator,
CLI discoverability, tests, and runtime automation are deferred to a
later gate.
**Architectural companion**:
[`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md)

---

## 1. Purpose

The Pane Registry records which visible operator-supervised pane is
bound to a live PCO claim on a host. It lets a reviewer reconstruct
the pane identity for a lane without treating terminal state as
authority.

The registry is a local runtime-state layer beside the Active-Work
Ledger. Active-Work Ledger claims remain authoritative for claim
lifecycle; Worktree Leases remain authoritative for worktree
contention; Worker-Container records remain authoritative for
container policy and instance state. A Pane Registry record binds to
those substrates but does not replace them.

## 2. Runtime Directory Shape

Pane Registry records are ignored runtime state under:

```text
.hermes/active-work-ledger/
  panes/<controller-id>/<lane-id>.yaml
```

`panes/<controller-id>/<lane-id>.yaml` is the latest pane-identity
record for the `(controller_id, lane_id)` pair. It MUST NOT be added
to the Git index. Future writers SHOULD use the same temp-file +
`fsync(2)` + `rename(2)` discipline used by the Active-Work Ledger.
Future validators MUST skip orphaned `*.tmp.*` files.

## 3. Record Shape

A Pane Registry record carries these discriminators:

| Field | Required value |
|---|---|
| `kind` | `pane-registry-record` |
| `record_type` | `pane_identity` |
| `schema_version` | `"1"` |

Required fields:

| Field | Purpose |
|---|---|
| `controller_id` | Controller that owns the bound claim. Same format and caveats as the Active-Work Ledger. |
| `lane_id` | Lane bound by the pane. Same format as the Active-Work Ledger. |
| `claim_ref` | Path to the Active-Work Ledger claim this pane serves. |
| `host_id` | Stable non-secret host identifier. |
| `pane_id` | Stable pane identifier within the host. |
| `role` | Pane Registry role, per §4. |
| `status` | Pane lifecycle status, per §5. |
| `record_timestamp` | Timestamp for this record write. |
| `registered_at` | Timestamp when the pane first registered for the claim. |
| `last_seen_at` | Timestamp when the pane was last observed alive. |

Optional fields:

| Field | Purpose |
|---|---|
| `claim_record_sha256` | SHA256 of the bound claim record observed at registration or heartbeat time. |
| `closed_at` | Terminal timestamp for `closed` / `aborted` statuses. |
| `close_reason` | Human-readable terminal reason. |
| `terminal` | Terminal identity object, per §6. |
| `worktree_path` | Advisory worktree path copied from the claim context. |
| `branch` | Advisory branch copied from the claim context. |
| `envelope_ref` | Assignment Envelope pointer. |
| `handoff_ref` | Handoff pointer. |
| `recommended_prompt_ref` | Recommended-prompt pointer. |
| `container_instance_id` | Optional Slice 2I-S / 2I-R container instance binding. |
| `container_instance_ref` | Optional pointer to the container-instance record. |

Future schemas SHOULD reject unknown top-level fields so the record
remains auditable.

## 4. Role Semantics

Pane Registry `role` names the lane function visible in the pane. The
v1 roles are:

| Role | Meaning |
|---|---|
| `architect` | Architecture or spec authoring pane. |
| `implementer` | Implementation pane. |
| `reviewer` | Review pane. |
| `verification` | Verification or test-evidence pane. |

These are not Slice 2I-S worker-container policy roles. Container
policy roles remain `architect_research`, `implementer`, and
`verification`; they govern isolation defaults for containers. Pane
Registry roles govern visible-pane identity. Any future Pane Registry
role addition MUST be justified in the protocol and validator docs.

## 5. Status Lifecycle

Valid statuses:

| Status | Meaning |
|---|---|
| `starting` | Pane spawn or handoff is in progress; identity is not yet confirmed active. |
| `active` | Pane is currently serving the bound live claim. |
| `blocked` | Pane remains bound to the claim but cannot progress without external input or a separately ratified action. |
| `closing` | Pane is ending and is expected to transition to a terminal state. |
| `closed` | Pane ended normally. `closed_at` and `close_reason` are required. |
| `aborted` | Pane ended abnormally or was operator-aborted. `closed_at` and `close_reason` are required. |

`active`, `blocked`, and `closing` records MUST bind to a live,
unreleased claim in future cross-record validation. A later validator
MAY refuse duplicate active panes for the same claim and role when
the contract forbids duplicates.

## 6. Terminal Identity

When a record claims `visibility: operator_visible` or equivalent
operator-supervised compliance, `terminal.kind` MUST be `tmux` and
the record MUST include enough tmux identity to locate the pane:
`session_id`, `window_id`, and `pane_id`.

`terminal.kind: plain_terminal` and `terminal.kind: unknown` MAY be
accepted only as transitional or legacy evidence categories. They do
not satisfy visible/operator-supervised compliance.

The terminal identity object MAY include advisory host-local
`pane_tty` or `pane_pid` fields, but these are non-authoritative and
MUST NOT contain secrets.

## 7. Container Binding

`container_instance_id` and `container_instance_ref` are optional. A
non-container visible pane remains valid.

When present, the container binding MUST refer to a Slice 2I-S /
2I-R container-instance record whose claim binding matches the pane's
`controller_id`, `lane_id`, and `claim_ref`. The Pane Registry does
not start, stop, inspect, or garbage-collect containers; it records
the identity relationship only.

## 8. Predicate Reservation

The future schema/validator gate reserves these additive PCO codes,
starting after Slice 2I-S `PCO-040` through `PCO-045`:

| Code | Future check |
|---|---|
| `PCO-046` | Pane Registry record schema. |
| `PCO-047` | Pane id, host id, controller id, and lane id format. |
| `PCO-048` | Role and status enum validity. |
| `PCO-049` | Required tmux identity for operator-visible compliance. |
| `PCO-050` | Active pane binds to a live unreleased claim. |
| `PCO-051` | Duplicate active pane for a claim/role where forbidden. |
| `PCO-052` | Container-instance binding exists and matches claim context when present. |
| `PCO-053` | Unknown field refusal / strict schema posture. |

If live `main` later reserves any of these codes before the
implementation gate, the implementation gate MUST choose the next
free additive range and update this protocol before landing code.

## 9. Explicit Non-Goals

Slice 3 spec/protocol authoring does NOT introduce:

- a schema, examples, validator, tests, or CLI command;
- pane-spawn automation or a Hermes runtime hook;
- runtime/provider/MCP/plugin configuration changes;
- Slice 4 Side-Effect Ledger records;
- Slice 5 `pco-fanin`;
- Slice 6 Integration Queue behavior;
- Slice 2I-R container runtime, credential broker, egress primitive,
  image choice, or allocator extension;
- team-mode Feature 007 Project Coordination Ledger, Feature 008
  source-host/tracker connectors, or Feature 009 distributed
  identity;
- GitHub, tracker, CI, deployment, or other external side effects.

## 10. Future Evidence

The future implementation gate MUST provide:

- `--list-checks` discoverability for the Pane Registry check(s);
- focused Pane Registry scan command discoverability;
- well-formed and malformed examples;
- stable PCO-code failures for missing required fields, invalid id
  patterns, invalid role/status values, missing tmux identity for
  visible compliance, unknown fields, missing/released claim binding,
  duplicate active panes where forbidden, and invalid container
  binding;
- tests proving read-only behavior, `*.tmp.*` skip behavior, and
  composition with Active-Work Ledger, Worktree Lease, and
  container-instance fixtures.
