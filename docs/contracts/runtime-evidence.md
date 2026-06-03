# Contract: Runtime Evidence Chain

Gate: v3 **G-1.3a** — the hash-chained evidence-spine substrate (fourth and
final slice of G-1, plane C / runtime safety).
Validator check: `ce_runtime_evidence`
Schema: `schemas/runtime-evidence.schema.yaml`
Pure substrate: `validators/creator_engine_validator/runtime_evidence_spine.py`
Hash-chain provenance (reused discipline):
[`../operations/CE_EVENT_PROTOCOL.md`](../operations/CE_EVENT_PROTOCOL.md)
(`ce-event-block` content-addressed chain) and
[`../operations/SIDE_EFFECT_LEDGER_PROTOCOL.md`](../operations/SIDE_EFFECT_LEDGER_PROTOCOL.md)
(append-only hash chain + genesis sentinel).

## Purpose

A Runtime Evidence chain is the **tamper-evident, append-only,
content-addressed audit spine** for one Creator Engine agent seat's runtime
lifecycle. It is the system of record CE keeps over (and independent of) any
backend's own logs: per the secure-runtime architect report, a rented runtime's
logs are a *source*, not the spine — CE keeps a signable, hash-chained evidence
trail so the runtime is *accountable*.

A reader with only a fresh clone must be able to read a chain and answer:

- which runtime-policy each record attests (`policy_sha`) and which provisioning
  run it belongs to (`run_id`);
- which lifecycle phase each record covers (`lifecycle_phase`:
  `provision` / `run` / `collect` / `teardown`);
- the classifier verdict category for the attested event (`classification`:
  `allowed` / `denied` / `escalate`); and
- whether the chain is intact — no record mutated, reordered, truncated, or
  unlinked (`content_hash`, `prev_hash`, `sequence`).

This contract is **defensive**: it makes the Creator Engine's own runtime audit
trail tamper-evident. It is never an offensive capability, and it allocates no
container, invokes no runner backend, opens no socket, and taps no live runtime.

## Hash-chain discipline (reused, not reinvented)

The spine mirrors the two landed in-repo hash chains (`ce-event-block` and the
side-effect ledger):

- **Content addressing.** `content_hash` is the SHA256 of the canonical JSON of
  the record material *excluding* the `content_hash` field itself — the exact
  `ce_event_block` canonical rule (`sort_keys=True`, separators `(",", ":")`,
  `ensure_ascii=False`). Because `prev_hash` and `sequence` are part of the
  material, tampering with either also breaks the content address.
- **Chain linkage.** Every record carries `prev_hash`. The **genesis** record
  (`sequence: 0`) uses the **all-zero SHA256 sentinel**
  (`0000000000000000000000000000000000000000000000000000000000000000`); every
  non-genesis record's `prev_hash` MUST equal the prior record's `content_hash`.
- **Monotonic sequence.** `sequence` is contiguous from `0`; a gap or reorder is
  refused (it signals truncation or reordering).
- **Policy binding.** Every record carries a `policy_sha` matching
  `^[0-9a-f]{64}$` — the digest of the runtime-policy it attests — so each
  attestation is anchored to the exact policy version in force.

The PURE `append` / `verify_chain` functions in `runtime_evidence_spine.py`
implement this discipline over in-memory records with no I/O.

## Predicate table (`ce_runtime_evidence`)

| Error code | When it fires |
|---|---|
| `runtime_evidence_schema_violation` | Record/chain fails `schemas/runtime-evidence.schema.yaml`. |
| `runtime_evidence_invalid_record` | File is unreadable or not a YAML mapping. |
| `runtime_evidence_content_address` | A record's `content_hash` ≠ the recomputed canonical hash (mutation). |
| `runtime_evidence_chain_link` | Genesis `prev_hash` ≠ the all-zero sentinel, or a non-genesis `prev_hash` ≠ the prior record's `content_hash`. |
| `runtime_evidence_sequence_break` | `sequence` is not contiguous from 0 (reorder / truncation). |
| `runtime_evidence_policy_unbound` | `policy_sha` is absent or not a `^[0-9a-f]{64}$` digest (record unbound from its policy). |

A file is treated as a candidate Runtime Evidence chain when it is a `.yml` /
`.yaml` file (not under `schemas/` or `templates/`, basename without `.tmp.`)
whose loaded YAML is a mapping with `kind: runtime-evidence-chain`.

## Scope boundary (what G-1.3a does NOT do)

G-1.3a is the **substrate**: the schema, the pure append/verify functions, and
the dogfood check over static records. It does NOT classify live events or wire
the spine into the runner lifecycle. The **classifier** (`event` →
`allowed`/`denied`/`escalate`, evaluated against the `ce_runtime_policy` record)
and the **audit overlay** (a backend-agnostic decorator over the `RunnerBackend`
provision/run/collect/teardown lifecycle that emits these records) are the
deferred **G-1.3b** slice. An OpenShell backend remains a later fast-follow
behind the same runner adapter.
