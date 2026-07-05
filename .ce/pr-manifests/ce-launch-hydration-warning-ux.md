# PR path manifest — canary-C UX gap (no ce-ops ticket) · Hydration warning UX

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-launch-hydration-warning-ux` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=9de2c4bfb2ec27a63be8ac3e8c685b08f9b9c2006c250b67f3a2829f82c4c0b9

```text
.ce/changelog/ce-launch-hydration-warning-ux.md
.ce/pr-manifests/ce-launch-hydration-warning-ux.md
validators/creator_engine_validator/launch_runtime.py
validators/tests/unit/test_launch_runtime.py
```
