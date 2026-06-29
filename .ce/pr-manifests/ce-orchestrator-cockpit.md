# PR path manifest — ce-ops#616 · Orchestrator read-only cockpit status

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-orchestrator-cockpit` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** feature

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=f7fc8254a4aa763c4be6cd244404503d8981cb64da7ad42c345ed8be15b07234

```text
.ce/changelog/ce-orchestrator-cockpit.md
.ce/pr-manifests/ce-orchestrator-cockpit.md
.ce/reference/cli.generated.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/orchestrator_status.py
validators/tests/unit/test_orchestrator_status.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
