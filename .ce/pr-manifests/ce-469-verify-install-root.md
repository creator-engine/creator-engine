# PR path manifest - ce-469-verify-install-root - verify requested install root

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-469-verify-install-root` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e5cbf4771f875e8058dfb4c2728842acfa68f1b854567aa4099eb319aff2b658

```text
.ce/changelog/ce-469-verify-install-root.md
.ce/pr-manifests/ce-469-verify-install-root.md
validators/creator_engine_validator/ce_provenance.py
validators/tests/unit/test_ce_provenance.py
```
