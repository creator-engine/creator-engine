---
slug: ce173-idempotent-reinstall
ticket: ce-ops#173
type: feature
scope: installer reinstall convergence
---

Adds explicit idempotent / overwrite-safe reinstall planning for the v3
installer path.

- Verifies signed bootstrap artifacts before persistent reinstall decisions.
- Plans deterministic repair/reuse for `.ce` scaffold state, verified venvs,
  GitHub App config/identity, JIT minted tokens, and interrupted apply ledgers.
- Refuses non-CE scaffold conflicts and unknown prior-state labels instead of
  guessing or clobbering.
- Adds shell bootstrap coverage for partial/corrupt venv repair without manual
  teardown.
