---
slug: ce-n3-dualformat-sync-gate
date: 2026-07-10
kind: added
scope: validator PR preflight
issue: none
---

**Dual-format sibling sync gate.**

- Adds a PR-diff validator check for tracked Markdown/HTML sibling pairs.
- Wires the check into local validate-pr so a change to one sibling fails until
  the matching sibling is also touched.
- Adds focused unit coverage for paired updates, one-sided Markdown changes,
  one-sided HTML changes, and unpaired Markdown files.
