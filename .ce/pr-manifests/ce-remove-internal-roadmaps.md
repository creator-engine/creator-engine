# PR path manifest — ce-ops#249 · tombstone internal v3/v3.5 roadmaps in public repo

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-remove-internal-roadmaps` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=2fbee08e460046a4f15c3da726eea85ea251dee475534dc0a012ea76f2474a90

```text
.ce/changelog/ce-remove-internal-roadmaps.md
.ce/pr-manifests/ce-remove-internal-roadmaps.md
docs/v3-roadmap.md
docs/v3.5-roadmap.md
```
