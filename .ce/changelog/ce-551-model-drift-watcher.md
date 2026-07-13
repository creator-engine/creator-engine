---
slug: ce-551-model-drift-watcher
date: 2026-07-12
kind: added
scope: model drift observation
issue: ce-ops#551
---

**feat(daemons): add model drift watcher (M9).**

- Add a least-authority watcher for canon-pinned model, reasoning-effort, and Codex-version drift.
- Persist debounce state and emit controller-inbox alarms without remediation or credentials.
