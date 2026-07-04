# PR path manifest — creator-engine/ce-ops#440 · cev3 deprecation notice and internal-groups lock-in

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-440-s2-cev3-deprecation` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=45528c5d4da5f7c1413d71912cc50e002075bf821cae092c3765882fc15f2e5b

```text
.ce/changelog/ce-440-s2-cev3-deprecation.md
.ce/pr-manifests/ce-440-s2-cev3-deprecation.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_ce_cli_v3_shim.py
```
