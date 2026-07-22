---
slug: ce620-launch-wrapper-model-effort-floor
date: 2026-07-22
kind: fixed
scope: governed launch wrappers and dispatch receipts
issue: ce-ops#620
---

**Enforce the ratified model-tier and reasoning-effort floor at launch.**

- Resolve model and effort before spawning; Luna is refused for persistent
  seat/foreman roles, low effort clamps to medium with an auditable warning,
  and stale raw flags are removed before canonical args are injected.
- Reassert the resolved Terra/high standing policy when DGX or VPS recreates a
  contained Codex configuration after stale session state.
- Require dispatch receipts to carry the canonical resolved model/effort stamp
  instead of arbitrary nonempty status prose.
