---
slug: ce196-queue-hygiene-completeness
ticket: ce-ops#196
type: feat
scope: forge triage hygiene
---

Completes `ce pickup triage` candidate hygiene (follow-up to ce-ops#194) so the
planner also fails closed on three classes of still-open-but-not-ready issues.

- **done-but-still-open**: the linked PR has merged or closed-as-done while the
  issue stayed open is skipped (`done_pr`), not just open-PR-in-flight.
- **held**: an `AWAITING-OPERATOR` / `⏸️` hold marker in the issue body or a
  comment is skipped (`held_marker`).
- **meta/debug**: meta/debug/tracking labels are skipped as non-leaf work.
- Mirrors #194's paginated, fail-closed lookups: ambiguous linked-PR state and
  failed/malformed timeline or comment lookups exclude the candidate
  (`linked_pr_status_unavailable`, `hold_marker_status_unavailable`).
- Adds offline unit coverage for each class plus the fail-closed paths.
