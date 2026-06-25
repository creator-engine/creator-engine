---
slug: ce243-seat-review-transport-deputy-pr
date: 2026-06-25
kind: feat
scope: ce-ops
issue: 243
---

**contained-seat self-submit PR review via injected credential.**

Route a contained seat gh pr review through the transport-deputy injection seam; fail-closed without a valid injected cred; token-leak verified. Boundary: delivers seat reviews/opinions only, NOT wall-capable approvals (seat never holds the wall signing secret). Tests included. (ce-ops#243)
