---
slug: ce-l2-automerge-canary-livedata
date: 2026-06-30
kind: changed
scope: automerge canary live-data decision inputs
issue: L2
---

**Wire live PR data into the automerge canary decision path.**

- **Declared work class:** S
- Added pull-request-only live review, approver, declared work-class, and check evidence for automerge decisions.
- Kept merge-group and query-error paths fail-closed with empty advisory evidence.
- Reused shared work-class normalization for canary XS/S and legacy tiny/story acceptance.
