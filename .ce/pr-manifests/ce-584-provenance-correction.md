# PR path manifest — creator-engine/ce-ops#584 · Correct CE568 changelog ticket provenance

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-584-provenance-correction` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=df6f5451b65f50db52b5c773d204321ed399d5f8da9ee11205fdcb16d9b54e5e

```text
.ce/changelog/ce-584-provenance-correction.md
.ce/pr-manifests/ce-584-provenance-correction.md
```
