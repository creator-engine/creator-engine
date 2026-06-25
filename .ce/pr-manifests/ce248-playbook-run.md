# PR path manifest — ce-ops#248 · public PLAYBOOK.md list/show/run dry-run

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce248-playbook-run` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=1fe27c5a8e1adba6bc1668bdbc5bf0a65006a249366308a10d66d0e7a7a98ea8

```text
.ce/changelog/ce248-playbook-run.md
.ce/pr-manifests/ce248-playbook-run.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/playbook_runtime.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_playbook_runtime.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
