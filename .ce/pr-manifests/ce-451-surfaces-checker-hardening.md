# PR path manifest - ce-451-surfaces-checker-hardening

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-451-surfaces-checker-hardening` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=03ec2c5f892a5f1269addd37be1664bc6a9de1745044ac5387017e694b9714b3

```text
.ce/changelog/ce-451-surfaces-checker-hardening.md
.ce/pr-manifests/ce-451-surfaces-checker-hardening.md
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_surfaces_manifest.py
```
