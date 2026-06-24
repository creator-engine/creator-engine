# ce-ops#188 belt reviews-pickup (v1/v3 boundary-clean)

Adds the controller-side review-pickup leg of the belt: it scans open PRs, routes
each awaiting-review PR to a distinct **non-author** reviewer seat, and invokes
the existing ce-ops#151 stale-review reconciler so objectively superseded
`CHANGES_REQUESTED` reviews are auto-dismissed (with the audit trail) before a
scoped re-request.

Because the review leg couples to the v3 forge (`re_review` +
`github_repo_config`), it lives in a **v3** module, `forge/review_pickup.py`, and
is exposed as `cev3 review-pickup` (NOT the v1 `ce pickup`). The deterministic,
read-only GitHub Search/transport/token primitives shared with the v1 work-poller
were extracted into a boundary-neutral `pickup_search` core (in neither runtime
set → `shared`), so neither runtime crosses the v1⊥v3 boundary
(`version_boundary` clean; the frozen shared→version allowlist untouched). The v1
`pickup.py` keeps the work-poll + claim + launch legs and re-exports the shared
core for its CLI/callers.

Offline tests cover non-author assignment, existing reviewer requests, stale
review re-request, superseded-review dismissal, the seat/token fail-closed gates,
and the `cev3 review-pickup` JSON surface.
