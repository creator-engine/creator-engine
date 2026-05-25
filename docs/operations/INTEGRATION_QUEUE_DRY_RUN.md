# Integration Queue Dry-Run Protocol

**Gate**: v1.0 Gate 8 (v1.0 docs finalization + delivery rehearsal + Integration Queue dry-run seam)
**Requirement**: RV1-082
**Status**: **Dry-run seam landed** (`ce queue dry-run` / `ce queue inspect`,
`creator_engine_validator/integration_queue_dry_run.py`, schema
`schemas/integration-queue-dry-run.schema.yaml`, well-formed/malformed example
previews, and contract tests are on this gate's worktree). **No live Integration
Queue authority exists in v1.0.**
**Architectural companions**:
[`EVIDENCE_FAN_IN_PROTOCOL.md`](./EVIDENCE_FAN_IN_PROTOCOL.md),
[`PCO_FANIN_PROTOCOL.md`](./PCO_FANIN_PROTOCOL.md),
[`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md)

---

## 1. Purpose and boundary

The **Integration Queue** (PCO Slice 6) owns the *serialized canonical-branch
landing order across lanes* — the decision of which lane's verified work lands
on the canonical branch, in what order, under Source ratification. That live
behavior is **POST-V1**; it is named here as a forward reference only.

In v1.0 the Integration Queue exists **only as a local dry-run landing
preview**. `ce queue dry-run` reconstructs a deterministic, content-hashed
serialized landing order from **verified fan-in packet evidence** and writes it
as a read-only preview artifact. It is the queue equivalent of `ce fanin` (Gate
7): it *indexes and previews*, it does not act.

A dry-run preview carries **no authority**:

- It performs **no** live landing, enqueue, merge, pull request, branch, remote,
  GitHub, tracker, CI, deploy, provider, credential, or package mutation.
- `has_authority` is constrained to `false` and `mode` is constrained to
  `dry-run` in the schema, so a document asserting live authority fails
  validation.
- Source ratification remains the only authority transfer; Assignment Envelopes
  remain the authority for work; Active-Work Ledger claims remain the authority
  for lane lifecycle. The preview merely shows *what a serialized landing order
  would be* given the evidence that already exists on disk.

## 2. What `ce queue dry-run` does

```text
ce queue dry-run --request <request.yaml> --preview-root <.hermes/integration-queue> [--repo-root <root>] [--preview-id <id>] [--json]
```

1. Reads a **dry-run request** (YAML or JSON) describing the lanes to serialize
   (see §4). It reads **only** local inputs.
2. Requires a Source-ratification reference (`prompt_ref` + `sha256`). A request
   without one is refused (`G8-QUEUE-MISSING-RATIFICATION`).
3. For each lane: verifies the referenced **fan-in packet** read-only via the
   landed Gate 7 `fanin_runtime.inspect` seam (content-hash + shape). A missing,
   unreadable, tampered, or stale packet is refused (`G8-QUEUE-FANIN-EVIDENCE`)
   — the preview rests on verified evidence, never lane self-report.
4. Reconstructs the serialized landing order from the lanes' `declared_order`,
   sorted to contiguous positions `1..N`. Two lanes claiming the same
   `declared_order` is refused (`G8-QUEUE-LANDING-CONFLICT`): a serialized
   landing requires a total order.
5. Records CE-event, PCL, and distributed-identity as **deferred-not-rejected**
   seam stubs (see §5).
6. Builds a preview payload with **no wall-clock fields**, computes the
   `content_hash` (SHA256 of the canonical preview bytes with `content_hash`
   removed), self-validates against the schema, and writes it to the
   **content-addressed** path `{preview_id}-{content_hash}.json` under the
   preview root.

Because the payload contains no timestamps or other nondeterministic fields,
**identical inputs produce byte-identical output**: same content hash, same
filename, same bytes. A rebuild is idempotent.

### Output location

The preview root **must be git-ignored** when it lives inside a repository
(verified with a read-only `git check-ignore`, the same discipline as
`ce fanin build` and `ce lane archive`). The canonical location is
`.hermes/integration-queue/`, which is ignored. A non-ignored root inside a repo
is refused (`G8-QUEUE-PREVIEW-ROOT-NOT-IGNORED`) so a preview — which embeds
local paths and evidence references — never reaches the tracked tree.

### Refusal-only authority flags

`ce queue dry-run` exposes `--enqueue`, `--land`, and `--merge` **only** as
refusal flags. Passing any of them refuses fail-closed
(`G8-QUEUE-AUTHORITY-REFUSED`) **before any read or write**, leaving the preview
root byte-identical. There is no flag, env var, or request field that turns the
dry-run seam into a live landing path; live landing is a separately ratified
POST-V1 Slice 6 surface.

## 3. What `ce queue inspect` does

```text
ce queue inspect --preview <preview.json> [--json]
```

`inspect` is read-only. It loads an existing preview, validates its shape against
`schemas/integration-queue-dry-run.schema.yaml`, recomputes the content hash over
the canonical bytes (with `content_hash` removed), and reports `ok` plus any
issues. A schema or hash failure yields a non-zero exit; it never mutates tracked
files and grants no authority.

## 4. Dry-run request format

```yaml
kind: integration-queue-dry-run-request
schema_version: "1"
preview_id: pco-v1-g8-queue-dry-run-example   # ^[a-z][a-z0-9-]{2,127}$
source_ratification:
  prompt_ref: .hermes/research/.../NEXT_..._VISIBLE_LANE_PROMPT.md
  sha256: <64 hex>
lanes:
  - lane_ref: pco-lane-with-ledger
    fanin_packet_ref: ../evidence-fan-in/with-ledger.json   # relative to the request file
    declared_order: 1
  - lane_ref: pco-lane-evidence-only
    fanin_packet_ref: ../evidence-fan-in/evidence-only.json
    declared_order: 2
seam_stubs:            # optional; sensible deferred-not-rejected defaults are applied
  ce_event: { note: "..." }
  pcl: { note: "..." }
  distributed_identity: { note: "..." }
```

The produced preview (`kind: integration-queue-dry-run-preview`) carries
`mode: dry-run`, `has_authority: false`, the serialized `landing_order` (each
entry pinning the verified `fanin_content_hash`), the `seam_stubs`, and the
`content_hash`. See `examples/well-formed/integration-queue-dry-run/` for a
committed request + preview pair, and
`examples/malformed/integration-queue-dry-run/` for previews that fail
validation (authority assertion, non-dry-run mode, tampered content hash).

## 5. Deferred-not-rejected seam stubs

Every preview records three team-mode / post-v1 seams as **stubs only**, with
`status: deferred-not-rejected`. They are recorded so the queue can reference
them cleanly when Source later ratifies team mode; recording a stub implies **no
active integration**:

| Seam | Disposition |
|---|---|
| **CE-event protocol (signed blocks)** | Team-mode coordination seam; not implemented in v1.0. |
| **PCL (Project Coordination Ledger)** | Team-mode materialized state seam; not implemented in v1.0. |
| **Distributed identity substrate** | Post-v1 multi-developer identity seam; not implemented in v1.0. |

## 6. Refusal codes

| Code | Condition |
|---|---|
| `G8-QUEUE-AUTHORITY-REFUSED` | a live `--enqueue` / `--land` / `--merge` action was requested |
| `G8-QUEUE-REQUEST-ERROR` | malformed request (bad kind, missing `preview_id`, empty/invalid `lanes`) |
| `G8-QUEUE-MISSING-RATIFICATION` | request lacks a `source_ratification` (`prompt_ref` + `sha256`) |
| `G8-QUEUE-FANIN-EVIDENCE` | a referenced fan-in packet is missing, unreadable, tampered, or stale |
| `G8-QUEUE-LANDING-CONFLICT` | two lanes claim the same `declared_order` (no total landing order) |
| `G8-QUEUE-PREVIEW-ROOT-NOT-IGNORED` | the preview root is inside a repo but not git-ignored |
| `G8-QUEUE-INSPECT-ERROR` | the preview file itself cannot be read during `inspect` |

Every `build` refusal raises **before any write**, leaving the preview root
byte-identical.

## 7. Relationship to Slice 6 (live Integration Queue)

The live Integration Queue — serialized canonical-branch landing executed under
Source ratification — is **POST-V1 Slice 6**, separately ratified and
unimplemented. This dry-run seam exists so v1.0 can *rehearse and preview* the
serialized landing order over verified evidence without ever holding landing
authority. When Source later ratifies the live queue, the dry-run preview is the
read-only sibling that continues to index evidence; it never becomes the live
path by configuration.
