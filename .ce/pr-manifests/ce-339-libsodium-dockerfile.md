# PR path manifest — ce-ops#339 · Add libsodium runtime package to DGX seat image

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-339-libsodium-dockerfile` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=d1eccbb39d958f704a85c0e9b58fc0b5960c1392f3837e6567e1c33d1086fb8b

```text
.ce/changelog/ce-339-libsodium-dockerfile.md
.ce/pr-manifests/ce-339-libsodium-dockerfile.md
deploy/dgx-runsc/Dockerfile
```
