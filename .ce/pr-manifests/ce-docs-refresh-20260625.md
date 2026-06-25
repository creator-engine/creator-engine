# PR path manifest — ce-ops#191 · refresh repo docs to current state

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-docs-refresh-20260625` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=f610a796919601e778a7ab6656841720b58fd505d03ecc0f5bc4695b63365889

```text
.ce/changelog/ce-docs-refresh-20260625.md
.ce/pr-manifests/ce-docs-refresh-20260625.md
README.md
docs/v3-roadmap.md
docs/v3.5-roadmap.md
```
