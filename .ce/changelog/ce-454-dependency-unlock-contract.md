---
slug: ce-454-dependency-unlock-contract
date: 2026-07-05
kind: docs
scope: dependency unlock contract
issue: ce-454
---

**Dependency unlock contract.**

- Add a documentation-only dependency unlock contract for blocker declarations, re-evaluation events, unlock mutation semantics, idempotency, replay guards, and fail-closed behavior.
- Add the new contract page to the seeded doctrine coverage exception list in `.ce/brain/doctrine-coverage.yaml`.
- Keep executor code, workflow wiring, schemas, and privileged actions out of scope.
