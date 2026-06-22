---
slug: ce189-supersession-guard
ticket: ce-ops#189
type: feature
scope: forge courier push supersession guard
---

Adds a deterministic fail-closed supersession guard to the forge branch push
primitive.

- Refuses before any remote read or push when branch-added paths already exist
  on `origin/main`, branch paths overlap base-side changes, ADR numbers collide,
  the `origin/main -> branch` diff is net-negative beyond threshold, or the
  branch base is stale by commit count or age.
- Keeps the decision logic pure and value-free, with git fact collection isolated
  behind the existing injectable spawn seam.
- Extends offline push, forge-join, and adoption-driver tests so the guard is
  covered without live git or network access.
- Regenerates the validator build identity for the branch parent so the
  packaging contract remains green after squash-merge ancestry.
