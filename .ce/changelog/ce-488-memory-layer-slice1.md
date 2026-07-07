---
slug: ce-488-memory-layer-slice1
date: 2026-07-07
kind: changed
scope: validators / takeover
issue: ce-ops#488
work_class: honest
---

**Memory-layer hydration contract slice 1.**

- Added mediated append support for first-class `brain-decision` and `brain-lesson` records in `.ce/brain/assertions.yaml`.
- Added `ce brain hydrate --json` for deterministic active decisions, active lessons, and newest resume-state pointer output.
- Wired `ce takeover --dry-run --json` to include and summarize the brain hydration contract in its evidence packet.
- Remediated PR #888 findings F1-F5: deterministic resume content hashing, required memory provenance fields, hydration determinism and corrupt-ledger takeover pins, and private memory append helpers.
