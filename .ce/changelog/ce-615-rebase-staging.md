---
slug: ce-615-dispatch-receipts
date: 2026-07-19
kind: feat
scope: dispatch tooling / validator kernel / ce CLI
issue: ce-ops#615
---

**Slice 1: machine-readable dispatch-activation receipts — schema, library, and CLI.**

CE fleet dispatch suffers three activation-gap classes that previously required
human scrollback inspection to detect:

- **grant-without-wake** — claim granted, seat never woken (addressed by later slices)
- **dispatch-without-transport** — brief pointer sent, in-seat arrival unconfirmed
- **receipt-without-activation** — receipt written, seat not truly active (e.g. tmux
  `send-keys -l` + text in the same call silently drops the Enter on many tmux builds;
  a SEPARATE `C-m` call is the proven-safe pattern)

This slice makes receipts machine-readable so watchers can assert activation rather
than infer it from scrollback. It is transport-agnostic (tmux and herdr both covered).

**New artifacts:**

- `validators/creator_engine_validator/schemas/dispatch-receipt.v1.schema.yaml` —
  Draft 2020-12 schema for `ce.dispatch-receipt` v1 records. Required fields: kind,
  schema_version, emitted_at, brief_path, brief_sha256, transport {kind, target},
  activation {method, issued_at, separate_enter}, model_effort_line (per
  2026-07-19 Operator floor ruling: seat's model/effort must be recorded at dispatch),
  dispatcher, work_unit. Optional: claim fields, transport_verified_at, post_check.
  Storage: `.ce/state/dispatch-receipts/<slug>-<utcstamp>.json`.

- `validators/creator_engine_validator/dispatch_receipt.py` — shared library module
  (not v1 or v3-specific; no new ratchet edge). Provides:
  - `build_receipt(...)` — assemble + schema-validate a receipt dict
  - `patch_receipt(...)` — add transport_verified_at / post_check to an existing
    receipt (the idiomatic watcher-update pattern)
  - `write_receipt(...)` / `read_receipt(...)` — append-safe persistence + read-back
    with schema validation
  - `verify_receipt(receipt)` — pure computational check returning `list[ReceiptFailure]`
    with typed `gap_class` strings: `dispatch-without-transport` and
    `receipt-without-activation` (two sub-conditions: `activation.separate_enter` is
    `False`, or `post_check` is absent)
  - `sha256_file(path)` / `sha256_bytes(data)` — SHA256 helpers for brief/claim digests

- `ce dispatch-receipt emit` — build + persist a receipt from CLI flags; auto-computes
  brief SHA256 from the brief file when `--brief-sha256` is omitted; reports gap classes
  on stdout; supports `--json`

- `ce dispatch-receipt verify <file>` — read-only gap-class check against a persisted
  receipt; exits 0 on clean, 1 on any gap; supports `--json`

**Tests:** `validators/tests/unit/test_dispatch_receipt.py` — 39 focused unit tests
covering schema happy/sad paths, each activation-gap classification, write/read
round-trips, patch semantics, and CLI emit/verify integration. All pass.

**Slice 2 scope (not in this slice):** actual transport integration — the tmux
`send-keys` wrapper that emits receipts automatically, the herdr-send-keys adapter,
in-seat brief verification (re-read sha256 to set transport_verified_at), and the
watcher daemon that calls `verify_receipt` on live receipts and alerts on gap classes.
