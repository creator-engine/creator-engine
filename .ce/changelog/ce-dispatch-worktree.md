---
slug: ce-dispatch-worktree
date: 2026-06-24
kind: added
scope: validator engine (dispatch_worktree) / ce CLI
issue: ce-ops#200
---

**Collision-safe concurrent dispatch core (ce-ops#200): `dispatch_worktree`
composes the built worktree + lane-claim primitives so multiple builds run in
parallel without clobbering one shared checkout.**

- New `dispatch_worktree.dispatch(spec, *, exec_fn, push_fn)`: acquire a forge
  work-claim → allocate a governed git worktree (`pco_allocator`) → run the
  harness in that worktree under a scrubbed env (`worker_spawn`) → push the branch
  on success → ALWAYS release the worktree then the claim in a `finally`.
- Fail-closed at every stage (claim / allocate / exec / push); **refuses before
  any worktree or exec on a foreign active claim** — the collision-safety core.
- `ce dispatch worktree` CLI emits the JSON outcome. Composes existing primitives
  (`pco_allocator`, `work_claims`, `worker_spawn`) — no reinvention. PR-1 of 2
  (PR-2 = container worktree-root mount + live smoke-test).
