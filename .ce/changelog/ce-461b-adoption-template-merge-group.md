---
slug: ce-461b-adoption-template-merge-group
date: 2026-07-06
kind: fixed
scope: validators
issue: ce-ops#473
---

**adoption workflow template merge_group trigger parity.**

- Adds the merge queue `merge_group: checks_requested` trigger to the emitted adopted-repo CE validation workflow template.
- Covers the emitted template with a regression test that parses the generated workflow trigger block.
