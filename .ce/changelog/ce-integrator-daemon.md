---
slug: ce-integrator-daemon
date: 2026-06-24
kind: added
scope: validator engine (forge.integrator_belt) / ce CLI (queue daemon)
issue: ce-ops#218
---

**Integrator belt DAEMON (ce-ops#218): autonomous, fail-closed merge of
approved-on-current-head + green + carrier-pass PRs under the merge gate.**

- `forge.integrator_belt` adds `run_daemon_pass` / `run_daemon_loop`: discover
  open PRs in a scoped repo/org, gate each with `_daemon_gate_refusal`, sequence
  by carrier path-set, and enqueue eligible PRs to the GitHub merge queue
  (`gh pr merge --auto`). Supports `--once` / `--loop` / `--dry-run`.
- Fail-closed gate refuses on: draft, `reviewDecision != APPROVED`, approval not
  on the current head SHA, not `MERGEABLE`, incomplete file/check pages, rollup
  `!= SUCCESS`, governance check missing/red, any test check red, and
  missing/unreadable/invalid carrier manifest. Path-overlap defers the second PR
  so no two conflicting PRs merge concurrently.
- A scoped daemon refuses to run unscoped; `--dry-run` merges nothing; no
  force-push path. Stage 2 of the ce-ops#218 poller→daemon arc.
