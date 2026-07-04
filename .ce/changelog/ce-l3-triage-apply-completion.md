---
slug: ce-l3-triage-apply-completion
date: 2026-07-04
kind: changed
scope: ce-ops triage queue automation
issue: ce-ops#67
---

**L3 triage apply-mode completion.**

- Create the triage queue sentinel comment in apply mode when absent, then patch it on later runs.
- Flip scheduled triage queue runs to apply mode with CE_TRIAGE_APPLY_KILL_SWITCH as the rollback switch.
- Add unit coverage for exactly-once sentinel creation, scheduled kill-switch wiring, and bounded apply mutations.
