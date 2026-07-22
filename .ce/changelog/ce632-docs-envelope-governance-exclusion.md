---
slug: ce632-docs-envelope-governance-exclusion
date: 2026-07-22
kind: fixed
scope: automerge policy — docs-envelope governance exclusions
issue: ce-ops#632
---

**Keep governance-class documentation outside the docs-envelope source predicate.**

- The docs-envelope predicate now derives its documentation-subtree exclusions
  from the mutation classifier's governance policy instead of maintaining a
  second list.
- Governance paths under `docs/contracts/`, `docs/decisions/`, `docs/adr/`,
  and `docs/governance/` fail the source predicate even when their extension is
  otherwise allowed; ordinary documentation remains permitted.
- Focused tests bind the predicate exclusions to the classifier source and
  cover every current governance documentation subtree.
- Coupling sweep found no brain assertion evidence pin and no generated-doc or
  reconciliation consumer. The ADR predicate reference was updated to record
  the classifier-derived exclusion.
