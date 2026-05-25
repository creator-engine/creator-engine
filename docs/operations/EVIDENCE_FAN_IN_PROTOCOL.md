# Evidence Fan-In Protocol

**Gate**: v1.0 Gate 7 (local read-only evidence fan-in packet)
**Requirements**: RV1-070, RV1-071
**Status**: **Runtime landed** (`ce fanin build` / `ce fanin inspect`,
`creator_engine_validator/fanin_runtime.py`, schema
`schemas/evidence-fan-in-packet.schema.yaml`, well-formed/malformed example
packets, and unit + integration tests are on this gate's worktree).
**Architectural companions**:
[`SIDE_EFFECT_LEDGER_PROTOCOL.md`](./SIDE_EFFECT_LEDGER_PROTOCOL.md),
[`TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md),
[`../architecture/parallel-controller-orchestration.md`](../architecture/parallel-controller-orchestration.md)

---

## 1. Purpose

The evidence fan-in packet is a **deterministic, content-hashed aggregation of
local evidence** produced for one gate or lane. It collects the evidence
manifests (`sha256sum`-style files) and Side-Effect Ledger chain references that
already exist on disk into a single stdlib-JSON document so a reviewer — human or
agent — can inspect one self-verifying artifact instead of re-walking the
evidence tree.

A fan-in packet is **read-only evidence**. It does not grant authority, does not
land work, does not enqueue anything for integration, and does not ratify
anything. Assignment Envelopes remain the authority for work; Active-Work Ledger
claims remain the authority for lane lifecycle; Source ratification remains the
only authority transfer. The packet merely *indexes and verifies* evidence that
others authored.

## 2. What `ce fanin build` does

```text
ce fanin build --request <request.yaml> --packet-root <.hermes/fan-in> [--repo-root <root>] [--packet-id <id>] [--json]
```

1. Reads a **fan-in request** (YAML or JSON) describing the local evidence to
   aggregate (see §4). It reads **only** local inputs.
2. Requires a Source-ratification reference (`prompt_ref` + `sha256`). A request
   without one is refused (`G7-MISSING-RATIFICATION`).
3. For each evidence manifest: confirms the manifest file's own SHA256 matches
   the request's pinned `manifest_sha256` (drift ⇒ **stale**,
   `G7-STALE-EVIDENCE`), then verifies every `<sha256>  <path>` entry against the
   referenced file's actual bytes (mismatch or missing file ⇒ `G7-SHA-MISMATCH`).
4. Optionally aggregates Side-Effect Ledger chain references by running the
   read-only `ce ledger verify` seam over a referenced ledger root; a ledger that
   fails verification is refused (`G7-LEDGER-EVIDENCE`).
5. Builds a packet payload with **no wall-clock fields**, computes the
   `content_hash` (SHA256 of the canonical packet bytes with the `content_hash`
   field removed), self-validates the packet against the schema, and writes it to
   the **content-addressed** path `{packet_id}-{content_hash}.json` under the
   packet root.

Because the payload contains no timestamps or other nondeterministic fields,
**identical inputs produce byte-identical output**: the same content hash, the
same filename, the same bytes. A rebuild is idempotent.

### Output location

The packet root **must be git-ignored** when it lives inside a repository
(verified with a read-only `git check-ignore`, the same discipline as
`ce lane archive`). The canonical location is `.hermes/fan-in/`, which is ignored.
A non-ignored root inside a repo is refused (`G7-PACKET-ROOT-NOT-IGNORED`) so a
packet — which embeds local paths and evidence references — never reaches the
tracked tree.

## 3. What `ce fanin inspect` does

```text
ce fanin inspect --packet <packet.json> [--json]
```

`inspect` is read-only. It loads an existing packet, validates its shape against
`schemas/evidence-fan-in-packet.schema.yaml`, recomputes the content hash over
the canonical bytes (with `content_hash` removed) and compares it to the stored
value. It exits non-zero if the packet violates the schema (including a packet
that falsely asserts `has_authority: true`) or if the recomputed hash does not
match (tamper or non-canonical serialization). It never mutates tracked files and
never grants authority.

## 4. Fan-in request shape

The request is a local YAML/JSON document. Minimal example:

```yaml
kind: evidence-fan-in-request
schema_version: "1"
packet_id: pco-v1-g7-local
source_ratification:
  prompt_ref: ".hermes/research/.../NEXT_PCO_V1_G7_PROMPT.md"
  sha256: "df4e56aee5fa4c9a7b586dd19228ecd58dfa01250185bf96d8052a4008392bd1"
evidence_manifests:
  - manifest_ref: "evidence/SHA256SUMS_GATE7_RUNTIME.txt"
    manifest_sha256: "<the ratified SHA256 of that manifest file>"
side_effect_ledger:            # optional
  root_ref: ".hermes/side-effect-ledger"
```

- `manifest_ref` may be absolute or relative to the request file's directory.
  Entry paths inside a manifest may be absolute or relative to the manifest's
  directory.
- `manifest_sha256` is the **pinned, ratified** SHA of the manifest file itself;
  it is how staleness is detected (the manifest changed since ratification).
- `side_effect_ledger.root_ref` is optional; when present its chains are verified
  and their head references are embedded.

## 5. Packet shape

The packet is validated by `schemas/evidence-fan-in-packet.schema.yaml`. Key
fields:

- `kind: evidence-fan-in-packet`, `schema_version: "1"`, `packet_id`.
- `has_authority`: schema **`const false`** — a packet can never assert authority.
- `source_ratification`: `{ prompt_ref, sha256 }`.
- `evidence`: sorted list of `{ manifest_ref, manifest_sha256, entry_count,
  entries: [{ path, sha256 }] }`.
- `side_effect_ledger`: `{ root_ref, verified, chains: [{ controller_id, lane_id,
  record_count, head_sha256, last_record_ref }] }`.
- `content_hash`: SHA256 of the canonical packet bytes with `content_hash`
  removed.

## 6. Authority boundary

The fan-in packet carries **no authority**, by construction:

- `has_authority` is constrained to `false` at the schema layer.
- `ce fanin build` exposes `--ratify`, `--enqueue`, and `--land` only as
  **refusal-only** flags; any of them is refused immediately
  (`G7-AUTHORITY-REFUSED`) before any read or write.
- The runtime performs **no** git, GitHub, tracker, CI, deploy, provider, MCP,
  plugin, container, or network mutation. The only external commands it runs are
  read-only: `git check-ignore` (ignore guard) and the existing `ce ledger
  verify` chain replay. It never prints, stores, or hashes secret values.

Ratification, enqueueing, and landing happen only through the governed Source
pathway — never as a side effect of building or inspecting a fan-in packet.

## 7. Refusal codes

| Code | Condition |
|---|---|
| `G7-AUTHORITY-REFUSED` | a `--ratify`/`--enqueue`/`--land` authority action was requested |
| `G7-REQUEST-ERROR` | the fan-in request is missing, unreadable, or malformed |
| `G7-MISSING-RATIFICATION` | `source_ratification` is absent or missing `prompt_ref`/`sha256` |
| `G7-STALE-EVIDENCE` | a manifest's actual SHA256 ≠ its pinned `manifest_sha256` (changed since ratification) |
| `G7-SHA-MISMATCH` | an evidence entry's recorded SHA ≠ the referenced file's actual SHA, or the file is missing |
| `G7-LEDGER-EVIDENCE` | a referenced Side-Effect Ledger fails chain verification |
| `G7-PACKET-ROOT-NOT-IGNORED` | the packet root is inside a repo but not git-ignored |
| `G7-INSPECT-ERROR` | the packet file is missing or unreadable during `inspect` |

Every `build` refusal is **fail-closed**: it raises before any packet write, so a
refused build leaves the fan-in root byte-identical.
