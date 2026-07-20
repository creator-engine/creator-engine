# PR path manifest — DF4-N · Governed author mechanics preconditions

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref
arc-full-output-t2-mechanics-preconditions` and requires this PR's `base..HEAD`
diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=617abbc7a68fb9089e73393de2804d7ad1863137f2018a664f2817ec8d1ea68f

```text
.ce/changelog/arc-full-output-t2-mechanics-preconditions.md
.ce/pr-manifests/arc-full-output-t2-mechanics-preconditions.md
docs/contracts/authoring-a-governed-pr.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
```
