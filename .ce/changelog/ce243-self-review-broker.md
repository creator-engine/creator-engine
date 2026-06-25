---
slug: ce243-self-review-broker
date: 2026-06-25
kind: changed
scope: egress broker / contained-seat self-review
issue: ce-ops#243
---

**host-side Unix-socket self-review broker.**

Operationalizes contained-seat PR review submission through a host-side transport-deputy broker:
bounded Unix-socket JSON request, COMMENT / REQUEST_CHANGES only, APPROVE refused before any
source-host call, repo-scoped review credential minted outside the sandbox, and env-only `gh api`
injection. Enforces the author≠reviewer invariant: the PR author is resolved host-side
(`gh api repos/{repo}/pulls/{pr}`) and a seat reviewing its own PR is refused before any credential
mint — fail-closed when the author cannot be resolved (mirrors `forge/plan_approval.py` /
`forge/review_pickup.py`). Adds focused unit coverage for allow/refuse, the author-not-reviewer
guard, unresolvable-author fail-closed, missing credentials, redaction, request bounds, and
command/API shape.

Changed paths:

```text
.ce/changelog/ce243-self-review-broker.md
.ce/pr-manifests/ce243-self-review-broker.md
tools/egress-broker/README.md
tools/egress-broker/ce_egress_self_review_broker.py
validators/tests/unit/test_egress_self_review_broker.py
```
