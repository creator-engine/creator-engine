---
slug: ce-479-parity-matrix
date: 2026-07-06
kind: feat
scope: harness promotion matrix
issue: ce-ops#479
---

**Separate harness code support from live promotion.**

- Reworked the harness matrix into provider/ring rows with explicit `code-support`, `launch-wired`, `live-proven`, and `promotion-approved` cells.
- Added an unsigned harness promotion matrix gate and wired it into local `ce validate-pr` plus CI without registering it as a per-path check.
- Encoded current Claude, Codex, worker-lane, contained-controller scaffold, and ephemeral-controller provider promotion states.
- Superseded the stale validate workflow full-file SHA brain assertion in favor of the existing normalized merge-group projection assertion.
