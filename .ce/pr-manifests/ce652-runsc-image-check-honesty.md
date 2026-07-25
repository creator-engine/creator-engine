# PR path manifest — VPS runsc image-check honesty

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path set for this PR. CI verifies that the base-to-head diff equals
exactly this set; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=4231752e01a23bf673960bb4c1a875cd996378fb1a151a81848b25f3ff5434c2

```text
.ce/changelog/ce652-runsc-image-check-honesty.md
.ce/pr-manifests/ce652-runsc-image-check-honesty.md
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_surfaces_manifest.py
validators/tests/unit/test_vps_runsc_launcher.py
```
