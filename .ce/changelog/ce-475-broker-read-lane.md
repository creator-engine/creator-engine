---
slug: ce-475-broker-read-lane
date: 2026-07-06
kind: changed
scope: tools/egress-broker
issue: ce-ops#475
---

**Egress broker forge read lane.**

Adds read-only broker verbs for contained seats: `get-issue`, `get-pr`, and
`list-comments`. Requests carry only values; the host broker enforces the per-seat
rate cap, mints short-lived read-only GitHub App installation tokens at request
time, injects them only into trusted host `gh api` child environments, revokes
them, and emits audit lines for allow/refuse outcomes. Documents deferred seams
for `kind:own` parity and governed `web-fetch`.

No existing broker behavior is modified; the `audit.py` change is an additive
forge-read counter used by this lane.
