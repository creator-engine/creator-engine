---
slug: arc-full-output-t2-mechanics-preconditions
date: 2026-07-20
kind: changed
scope: governed author mechanics
issue: DF4-N
work_class: XS
---

**Document reportable governed-author mechanics preconditions.**

- Require reportable carrier-slug matching, base re-derivation, explicit staging,
  committed readiness, and work-class-floor evidence.
- Supersede the stale carrier-discipline assertion with the current committed
  `docs/contracts/authoring-a-governed-pr.md` SHA-256.
- Require programmatic `branch_slug(head_ref)` derivation and append-only brain
  supersession when a carrier edits a pinned document.
- After append-only rebase, regenerate the carrier-discipline successor from
  the target-main ledger rather than retaining stale branch ledger records.
- Keep the change limited to canonical author guidance and its PR carriers.
