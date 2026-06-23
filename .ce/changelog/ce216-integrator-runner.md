---
slug: ce216-integrator-runner
date: 2026-06-23
kind: added
scope: integrator runner
issue: ce-ops#216
---

Adds the Unit 5 one-shot Integrator MVP runner.

- Wires the existing Search API repair-needed detector to deterministic
  conflict resolvers, Unit 3 executor calls, and unresolved-conflict escalation.
- Keeps executor authority behind the Unit 3 API and fails closed when that
  dependency is not present on the base branch.
- Adds an injectable live-action callback to the Integration Queue dry-run seam
  so live queue requests are real only through the runner and otherwise refuse
  before preview writes.
