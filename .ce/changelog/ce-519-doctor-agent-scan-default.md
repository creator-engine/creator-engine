---
slug: ce-519-doctor-agent-scan-default
date: 2026-07-10
kind: fixed
scope: doctor
issue: ce-ops#519
---

**Run the coding-agent CLI scan in default doctor mode.**

- Surface a missing configured harness CLI as an advisory doctor finding by default.
- Preserve hard refusal for missing harness runtime when visible launch is required.
