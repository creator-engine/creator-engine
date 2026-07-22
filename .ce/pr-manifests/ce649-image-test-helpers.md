# PR path manifest — ce-ops#649 · Share image-contract token helpers

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce649-image-test-helpers` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=49ca22a7fb2128bf281d89b362f32f7742f2550043621fba88c7d59292b3cd8e

```text
.ce/changelog/ce649-image-test-helpers.md
.ce/pr-manifests/ce649-image-test-helpers.md
validators/tests/unit/image_contract_helpers.py
validators/tests/unit/test_oci_image.py
validators/tests/unit/test_runtime_image.py
validators/tests/unit/test_seat_image.py
validators/tests/unit/test_vps_runsc_image.py
```
