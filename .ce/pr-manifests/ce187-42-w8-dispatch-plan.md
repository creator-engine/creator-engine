# PR path manifest — ce-ops#187 / ce-ops#42 · Dry-run dispatch planner

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce187-42-w8-dispatch-plan` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=1049b449e82917a3aa1d62461e4cbf55d75b8a40e134c93382b8b9aa3f1e1fe2

```text
.ce/changelog/ce187-42-w8-dispatch-plan.md
.ce/pr-manifests/ce187-42-w8-dispatch-plan.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/dispatch_plan.py
validators/tests/unit/test_dispatch_plan.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
