# PR path manifest — 146 · SSDF/SLSA conformance matrix

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce146-ssdf-slsa-matrix` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=df11d3858f45f3de46bab3adb1084e60378b0735db17d2465af69255910e4620

```text
.ce/changelog/ce146-ssdf-slsa-matrix.md
.ce/pr-manifests/ce146-ssdf-slsa-matrix.md
docs/compliance/ssdf-slsa-conformance.md
```
