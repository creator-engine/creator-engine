---
slug: ce-n1s2-review-pickup-acting
date: 2026-07-10
kind: added
scope: review-pickup acting
issue: ce-n1s2-review-pickup-acting
work_class: M
---

**Add default-OFF review-pickup acting chain.**

Adds an explicitly armed reviewer-spawn and PR-comment path. The acting pass is
durably deduplicated, posts only through the Issues comments API, records
per-item failures without crash-looping, and requires an Operator-provided
spawn command template. The service remains unarmed by default.
