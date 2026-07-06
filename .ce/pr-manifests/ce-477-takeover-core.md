# PR path manifest — ce-ops#477 · Add ce takeover dry-run core

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-477-takeover-core` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=8e4efd946382a7c6c6d4c7986088073e8ac0c068d886635cfc3e02e904f10f38

```text
.ce/changelog/ce-477-takeover-core.md
.ce/pr-manifests/ce-477-takeover-core.md
.ce/reference/cli.generated.md
README.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/takeover_runtime.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_ce_takeover_cli.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
