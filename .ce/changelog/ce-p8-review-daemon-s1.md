---
slug: ce-p8-review-daemon-s1
date: 2026-07-09
kind: added
scope: review-pickup dry-run daemon slice 1
issue: ce-p8-review-daemon-s1
work_class: story
---

**Add review-pickup dry-run daemon slice 1 (advisory/observe-only).**

Adds `forge.review_dry_run` module wrapping `forge.review_pickup.poll_review_pickup(dry_run=True)` with an Operator-held gate and a named JSONL feed. Emits `WOULD_ASSIGN` and `WOULD_SKIP` decisions per PR per pass; no GitHub writes in any path. The Operator-held gate checks the `awaiting-operator` label (fail-open on API error) and an optional held-list file. Fourteen offline unit tests cover both gates and the bounded/rate-limited daemon loop. Slice 2 will add the `cev3 review-dry-run` CLI surface wired to `gate-daemons.env`.
