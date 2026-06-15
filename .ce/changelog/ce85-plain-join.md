---
slug: ce85-plain-join
date: 2026-06-15
kind: added
scope: install / onboard --apply
issue: ce-ops#85
---

**Add the plain-join path so a new dev can `onboard --apply` into an already-CE
repo.**

`onboard --apply` could not complete for a repo that is ALREADY CE-governed: it
refused `e2_brownfield_seam_unavailable`, because brownfield *adoption* (taking a
NON-CE project into CE, still E3-deferred) was auto-enabled for an
already-governed repo. This blocked `ce-dev-3` (VPS) and `ce-dev-4` (DGX) from
joining `creator-engine/creator-engine`.

Plain-join is a first-class, auto-detected E2 path — "a new dev joins an
ALREADY-CE repo" — distinct from brownfield adoption. No new user knob.

- New FAIL-CLOSED detector `repo_is_already_ce_governed`: already-CE iff the repo
  is reachable AND the CE validate workflow is present at the pinned digest AND
  the branch-protection reference floor is present. Any uncertainty → NOT
  plain-join → the unchanged brownfield/E3 refuse (never silently proceeds).
- The `onboard --apply` gate and the `github_repo_create` leg route already-CE to
  plain-join (`already_satisfied` / `join_existing_ce_repo`); downstream legs
  verify/reconcile idempotently — the workflow is verified, never overwritten,
  and branch protection is reconciled so missing CE checks are ADDED while
  existing checks are NEVER removed (HARD requirement: runs against the live OSS
  repo).
- `--plan` surfaces the plain-join route (`plain_join.route`), closing the
  "plan-level only" honesty gap from the rehearsal.

Genuine brownfield (`mode==existing` and NOT already-CE) is unchanged: still
E3-deferred, mutates nothing. Detection has no live forge driver in this build,
so plain-join fails-closed to the E3 refuse in production until a live driver is
wired — the seam + logic land now, fully fake-driver tested.
