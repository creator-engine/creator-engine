# PR path manifest — ce-ops#380 · DGX launcher image manifest guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-380-dgx-launcher-image-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=de0ed9ec159cff0e58af1400b56c356a21118e566f5fb14d50f9d218df8572fc

```text
.ce/changelog/ce-380-dgx-launcher-image-guard.md
.ce/pr-manifests/ce-380-dgx-launcher-image-guard.md
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_surfaces_manifest.py
```
