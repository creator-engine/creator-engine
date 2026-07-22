# PR path manifest — ce-ops#595 · Package the canonical issue-reference parser

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce595-issue-refs-packaging` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=8ed45e0696f1ba9309356a2d98509e1d910b6d9dbc7305a44dd5b806a15c73c3

```text
.ce/brain/assertions.yaml
.ce/changelog/ce595-issue-refs-packaging.md
.ce/pr-manifests/ce595-issue-refs-packaging.md
tools/ce-ops-autoclose/parse_issue_refs.py
validators/creator_engine_validator/issue_refs.py
validators/creator_engine_validator/ticket_reconcile_feed.py
validators/tests/unit/test_issue_refs.py
validators/tests/unit/test_ticket_reconcile_feed.py
```
