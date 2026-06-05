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
- which lifecycle phase each lifecycle record covers (`lifecycle_phase`:
  `provision` / `run` / `collect` / `teardown`);
- the classifier verdict category for the attested event (`classification`:
  `allowed` / `denied` / `escalate`);
- the run's terminal **outcome**, when the run produced one (a typed
  `runtime_run_outcome` record: `outcome` ∈ `pr_opened` / `review_submitted` /
  `research_delivered` / `no_change`, plus a value-free `change_set` pointer — the
  disposition axis, orthogonal to `lifecycle_phase`); and
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

## Run-outcome records (v3 G-3.6a — the terminal-disposition axis)

A chain may end with a **typed run-outcome record** that attests WHERE the run
ended. This is a distinct record type (`kind: runtime-run-outcome`,
`record_type: runtime_run_outcome`) on an axis **orthogonal** to the container
`lifecycle_phase`: the lifecycle axis is universal (`provision` → `teardown`),
whereas the *outcome* is plural and work-type-dependent (a run may open a PR,
submit a review, deliver research, or change nothing). Modelling the outcome as a
`lifecycle_phase` value would conflate the two axes, so the outcome is its own
typed record and is **never** a `lifecycle_phase`.

- **Same chain, same integrity.** The outcome record is appended to the SAME
  hash chain via the pure `append` (content-addressed, `prev_hash`-linked,
  contiguous `sequence`, `policy_sha`-bound), so the terminal disposition is
  itself tamper-evident. `verify_chain` treats it like any record.
- **Required fields:** `kind` / `record_type` / `schema_version` / `policy_sha` /
  `run_id` / `sequence` / `prev_hash` / `content_hash` / `recorded_at` / `outcome`
  / `change_set`. It carries **no** `lifecycle_phase` and **no** `classification`.
- **`outcome`** is a string enum: `pr_opened` / `review_submitted` /
  `research_delivered` / `no_change`. The v3 MVP produces only `pr_opened`; the
  rest are reserved vocabulary for later slices.
- **`change_set`** is a value-free pointer — `branch` / `base` / `manifest_paths`
  / `head_sha` (+ optional `pr_number`). It carries NO diff, NO secret, and NO
  host / credential / account / registry identifier as a normative binding (the
  same prohibition that applies to every record).

A schema-conformant chain holds **either** record type per element; the two are
mutually exclusive (`kind` / `record_type` consts + `lifecycle_phase` vs
`outcome` select exactly one). A record with an out-of-enum `outcome` (or a
missing `change_set`) fails `runtime_evidence_schema_violation`. Worked example:
`examples/well-formed/runtime-evidence/example-runtime-evidence-chain-pr-opened.yml`.

## Scope boundary (what G-1.3a does NOT do)

G-1.3a is the **substrate**: the schema, the pure append/verify functions, and
the dogfood check over static records. It does NOT classify live events or wire
the spine into the runner lifecycle. The **classifier** (`event` →
`allowed`/`denied`/`escalate`, evaluated against the `ce_runtime_policy` record)
and the **audit overlay** (a backend-agnostic decorator over the `RunnerBackend`
provision/run/collect/teardown lifecycle that emits these records) are the
deferred **G-1.3b** slice. An OpenShell backend remains a later fast-follow
behind the same runner adapter.
