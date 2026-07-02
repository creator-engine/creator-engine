# PR path manifest — ce-404 · Wall remint on head mismatch

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-404-wall-remint-on-head-mismatch` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=6effb366d4698bb45f00edccf2628e5479d9c09d60242ff183b27860fb879c47

```text
.ce/changelog/ce-404-wall-remint-on-head-mismatch.md
.ce/pr-manifests/ce-404-wall-remint-on-head-mismatch.md
validators/creator_engine_validator/forge/integrator_belt.py
validators/tests/unit/test_integrator_belt.py
```
