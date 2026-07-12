# PR path manifest — ce-ops#544 · Disable inherited Git signing in the DGX seat image

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-544-seat-image-signing-strip` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=2345f89493e4c547b6ffce5b77ae95751eed70b48e5c4fd51c507d4a1370ae27

```text
.ce/changelog/ce-544-seat-image-signing-strip.md
.ce/pr-manifests/ce-544-seat-image-signing-strip.md
deploy/dgx-runsc/Dockerfile
validators/tests/unit/test_dgx_runsc.py
```
