# ce-ops#253 controller inbox

- Added a read-only v3 `inbox` command with `controller-inbox` alias for scoped controller awaiting-decision views.
- Bucketed scoped open PRs into `needs_review`, `stranded`, `needs_rebase`, and `awaiting_operator` with deterministic JSON and table output.
- Used GraphQL `repository.mergeQueue.entries` for stranded queue-membership checks; no auto-acting and no `autoMergeRequest` queue inference.
- Added offline unit coverage for bucket classification, queued versus unqueued approved clean PRs, table output, and CLI wiring.
