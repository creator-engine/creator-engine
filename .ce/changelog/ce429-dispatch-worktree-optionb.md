---
slug: ce429-dispatch-worktree-optionb
date: 2026-06-25
kind: fixed
scope: dispatch_worktree reaches v1 primitives via the v3_seat_bridge non-import seam (ratchet-clean)
issue: ce-ops#200
---

**dispatch_worktree — Option B (ratified).**

- `dispatch_worktree` now reaches the v1 runtime primitives through the existing `v3_seat_bridge` / `runtime_backend_bridge` non-import seam instead of importing v1 directly.
- No new shared→v1 import edge: the `version_boundary` ratchet passes with no allowlist change.
- Supersedes the rejected direct-import / `__import__` approaches on #429.
