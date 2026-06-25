---
slug: ce243-self-review-broker
date: 2026-06-25
kind: changed
scope: egress broker / contained-seat self-review
issue: ce-ops#243
head_sha: 24f17402ab1b55326746213807cf04903150c06d
---

**host-side Unix-socket self-review broker.**

Operationalizes contained-seat PR review submission through a host-side transport-deputy broker:
bounded Unix-socket JSON request, COMMENT / REQUEST_CHANGES only, APPROVE refused before any
source-host call, repo-scoped review credential minted outside the sandbox, and env-only `gh api`
injection. Adds focused unit coverage for allow/refuse, missing credentials, redaction, request
bounds, and command/API shape.

Changed paths:

```text
.ce/changelog/ce243-self-review-broker.md
.ce/pr-manifests/ce243-self-review-broker.md
tools/egress-broker/README.md
tools/egress-broker/ce_egress_self_review_broker.py
validators/tests/unit/test_egress_self_review_broker.py
```
