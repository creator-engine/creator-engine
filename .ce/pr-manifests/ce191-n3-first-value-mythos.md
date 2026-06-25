# PR path manifest — ce-ops#191 · first-value script for mythos (N3)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce191-n3-first-value-mythos` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e04dea17b10b57f508eaa1d5417cfa8adfa132a325a8a00300ace3937fbee365

```text
.ce/changelog/ce191-n3-first-value-mythos.md
.ce/pr-manifests/ce191-n3-first-value-mythos.md
docs/guide/first-value-mythos.md
scripts/first-value.sh
```
