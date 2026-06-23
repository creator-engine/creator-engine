---
slug: ce151-stale-review-reconcile
date: 2026-06-22
kind: added
scope: rebase-aware stale-review reconciliation (forge.re_review)
issue: ce-ops#151
---

Added `forge/re_review.py` — deterministic rebase-aware re-review reconciliation
(the reviews-automation half of the #188 belt reviews-pickup). Resolves
stale-review churn without manual controller dismissal (the recurring #309 toil).

Conservative auto-dismiss rule (the ONLY case that dismisses): a
`CHANGES_REQUESTED` review is dismissed iff its `commit_id` is no longer the PR
head AND the current head carries a fresh `APPROVED` review from a DIFFERENT
reviewer — the objection is objectively superseded by an independent approval on
the live head. Every other stale review is classified `RE_REQUEST_SCOPED`
(re-request, never auto-dismiss); a live objection on the head is `CURRENT` and
untouched. Every dismissal posts an audit comment naming the superseding
approval. The pure classifier (`classify_reviews`) is zero-I/O and exhaustively
unit-tested; all GitHub I/O flows through the injectable `GhRunner`. `apply=False`
is a read-only dry-run. `list_reviews` paginates the full review history
(`per_page=100`, walking every page until a short page proves completeness) and
fails closed on a page-ceiling overrun or a non-array body — incomplete state
must never reach the auto-dismiss path. CLI/belt-poll wiring follows as a
separate slice.
