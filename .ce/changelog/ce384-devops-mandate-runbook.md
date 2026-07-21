---
slug: ce384-devops-mandate-runbook
date: 2026-07-21
kind: added
scope: governed operations
issue: ce-ops#384
---

Adds the governed CE DevOps agent mandate and its evidence-first recovery
runbook seed. The role separates infrastructure diagnosis and contained recovery
from controller implementation and governance authority, while documenting
context, credential, broker, interpreter, and worker-host recovery boundaries.

The change also records the public-docs coupling: each net-new operations
document requires its own exact registration in the public-docs exception
ratchet in the same change. This preserves the current fail-closed boundary and
makes the coupling available for a future dedicated gate.
