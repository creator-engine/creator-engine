---
slug: ce259-worker-run
date: 2026-06-26
kind: added
scope: worker CLI/runtime
issue: ce-ops#259
---

Add `ce worker run --role <role> --brief <file>` as the sanctioned governed
role-brief path.

- Resolves checked-in role definitions from `.claude/agents/<role>.md` and
  fails closed for missing or unknown roles.
- Composes the existing `worker_spawn` launch primitive, seeds the launched pane
  with a pointer-only prompt/findings instruction, and returns structured
  findings through injectable seams for offline tests.
- Documents deferred follow-up for `architect_research` egress and
  declared-tools-vs-runtime capability reconciliation.
