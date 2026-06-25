---
slug: ce-wall-armed-demo
date: 2026-06-25
kind: chore
scope: governance
issue: ce-ops#247
---

**validate the approval-capability merge gate end-to-end.**

Exercise the approval-capability wall through one live governed merge: a minimal change that travels push -> governance-green -> reviewer approval -> capability-marker mint-on-approval -> merge. Confirms the armed gate admits exactly the approved, green path and nothing else.
