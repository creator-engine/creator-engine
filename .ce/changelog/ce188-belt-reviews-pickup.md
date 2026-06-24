# ce-ops#188 belt reviews pickup

Adds the controller-side review-pickup leg for the belt. `ce pickup reviews`
now scans open PRs, routes awaiting-review PRs to a distinct non-author reviewer
seat, and invokes the existing ce-ops#151 stale-review reconciler so objectively
superseded `CHANGES_REQUESTED` reviews are auto-dismissed with the audit trail
before re-requesting scoped review.

Offline tests cover non-author assignment, existing reviewer requests, stale
review re-request, superseded-review dismissal, and the CLI JSON surface.
