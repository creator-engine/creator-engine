# PR path manifest — ce-ops#166 · Add brain doctrine coverage ratchet

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-166-doctrine-coverage` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=e73f9ecacee14fd23d880a96646d2de95e42c96dd440a036e16c75d274c8ff32

```text
.ce/brain/doctrine-coverage.yaml
.ce/changelog/ce-166-doctrine-coverage.md
.ce/pr-manifests/ce-166-doctrine-coverage.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/ce_brain_doctrine_coverage.py
validators/tests/unit/test_ce_brain_doctrine_coverage.py
```
