---
slug: ce-triage-autolabel
date: 2026-07-01
kind: added
scope: ce-ops triage queue advisory labels
issue: ce-ops#67
---

**Add advisory classification labels to the ce-ops triage queue.**

- Apply-mode now synchronizes deterministic `wc:` and `triage:` issue labels from the existing advisory queue classification.
- Dry-runs report the would-be managed label delta without writing labels.
- Label errors are recorded per issue so the advisory queue can continue posting.
