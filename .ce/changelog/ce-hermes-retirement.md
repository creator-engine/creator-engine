---
slug: ce-hermes-retirement
date: 2026-07-08
kind: changed
scope: onboard state
issue: ce-ops#507
---

**Complete user-facing Hermes state retirement.**

- `ce onboard` now requires canonical `.ce/state/` bootstrap state instead of hard-requiring a `.hermes/` gitignore precondition.
- Legacy `.hermes/` directories are tolerated as advisory-only compatibility state.
- Updated CLI help, deployed runsc defaults, hook evidence roots, and functional docs to point at `.ce/state/`.
- Left v1-frozen templates and schema constants untouched for separate product follow-up.
