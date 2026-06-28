# PR path manifest — ce-ops#313 · Automerge status decision-log reader

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-automerge-status` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=6bccd6f9c56be594c32e56a3a14e2fc9d73d160f4723f4f26742a7bc7c5aed6e

```text
.ce/changelog/ce-automerge-status.md
.ce/pr-manifests/ce-automerge-status.md
.ce/reference/cli.generated.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_status.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
