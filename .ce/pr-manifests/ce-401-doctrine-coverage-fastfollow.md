# PR path manifest — ce-ops#401 · Harden doctrine coverage ratchet edge cases

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-401-doctrine-coverage-fastfollow` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=745a11b1e8a913846bf8988351c88688d2b7a9e4b4a2a9302770a01bc060f0c4

```text
.ce/changelog/ce-401-doctrine-coverage-fastfollow.md
.ce/pr-manifests/ce-401-doctrine-coverage-fastfollow.md
validators/creator_engine_validator/checks/ce_brain_doctrine_coverage.py
validators/tests/unit/test_ce_brain_doctrine_coverage.py
```
