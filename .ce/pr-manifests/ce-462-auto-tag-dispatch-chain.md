# PR path manifest — ce-ops#462 · fix: release-auto-tag explicit ordered dispatch (GITHUB_TOKEN suppression)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-462-auto-tag-dispatch-chain` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=cd4102ddfab2bbbb45e8c8b6465364af7319c12d285fef76a8dbf12e1e889aa0

```text
.ce/changelog/ce-462-auto-tag-dispatch-chain.md
.ce/pr-manifests/ce-462-auto-tag-dispatch-chain.md
.github/workflows/release-auto-tag.yml
validators/tests/unit/test_release_auto_tag_workflow.py
```
