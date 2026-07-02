---
slug: ce-387-holdlabel-symmetry
date: 2026-07-02
kind: fixed
scope: forge controller inbox
issue: ce-ops#387
---

**Hold-label symmetry for controller inbox.**

- Reused the full shared issue-side blocking hold-label union for PR awaiting-operator classification.
- Covered PR labels without body markers across the union: `wip`, `blocked`, `waiting`,
  `status:*` variants such as `status:checkpoint`, `do-not-claim`,
  `dependency-blocked`, existing awaiting-operator labels (`awaiting-operator`,
  `hold`, `awaiting-operator/hold`), and held/on-hold aliases including case variants.
