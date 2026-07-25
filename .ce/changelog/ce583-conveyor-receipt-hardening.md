---
slug: ce583-conveyor-receipt-hardening
date: 2026-07-25
kind: fixed
scope: conveyor receipt persistence and armed daemon
issue: ce-ops#583
---

Harden conveyor receipt persistence and armed daemon seams for ce-ops#583
slices 10–13 only.

- Require the live `os.replace(..., src_dir_fd=..., dst_dir_fd=...)` capability
  in the receipt platform probe, including CPython's documented `renameat`
  equivalence where `os.replace` is not enumerated separately.
- Replace armed-path assertions with explicit `ValueError` refusals so optimized
  Python cannot erase a required dependency check.
- Create JSONL side-effect ledgers with mode `0600`, and create private runtime
  directories atomically at `0700` while refusing unsafe pre-existing paths.

Slices 1–2, 6–9 of ce-ops#583 remain open and are deliberately untouched.
