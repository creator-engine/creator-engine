# PR path manifest — ce-ops#190 · feat: first-class ce update

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce190-ce-update-signed-inplace` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=7b29f5ed0795a6e5f3aa6e19d61926e7532fddc02511cc106d277f34d4de01fa

```text
.ce/changelog/ce190-ce-update-signed-inplace.md
.ce/pr-manifests/ce190-ce-update-signed-inplace.md
README.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/update.py
validators/tests/unit/test_ce_update.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_version_boundary.py
```
