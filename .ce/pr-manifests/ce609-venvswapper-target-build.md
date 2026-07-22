# PR path manifest — ce-ops#609 · Build VenvSwapper targets in place

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce609-venvswapper-target-build` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=ac121cf94a0562d06cc91fa5567bab3ddda02f8a4d28bf7b2bc56a9d47f206bc

```text
.ce/changelog/ce609-venvswapper-target-build.md
.ce/pr-manifests/ce609-venvswapper-target-build.md
validators/creator_engine_validator/main_head_install.py
validators/creator_engine_validator/update.py
validators/tests/unit/test_ce_update.py
validators/tests/unit/test_main_head_install.py
```
