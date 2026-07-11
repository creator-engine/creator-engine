---
slug: repair-n1s2-review4-dev3
date: 2026-07-10
kind: added
scope: review-pickup acting
issue: ce-n1s2-review-pickup-acting
---

**Add default-OFF review-pickup acting chain.**

Adds an explicitly armed reviewer-spawn and PR-comment path. The acting pass is
durably deduplicated, posts only through the Issues comments API, records
per-item failures without crash-looping, and requires an Operator-provided
spawn command template. The service remains unarmed by default.
