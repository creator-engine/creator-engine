# PR path manifest — ce-ops#187 / ce-ops#42 · Dry-run dispatch planner

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce187-42-w8-dispatch-plan` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=2782b0799d69c31e3289636447c4f8e5fc43e5943239d86ee508b59d9aecd2b1

```text
.ce/changelog/ce187-42-w8-dispatch-plan.md
.ce/pr-manifests/ce187-42-w8-dispatch-plan.md
.ce/reference/cli.generated.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/dispatch_plan.py
validators/tests/unit/test_dispatch_plan.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
