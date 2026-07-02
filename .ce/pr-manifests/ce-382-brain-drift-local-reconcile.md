# PR path manifest — ce-ops#382 · Local brain drift reconcile

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-382-brain-drift-local-reconcile` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=261ed2b1f6950626e2d60a7e471f944f6965c387cb307cf7a5280d1a8df28787

```text
.ce/changelog/ce-382-brain-drift-local-reconcile.md
.ce/pr-manifests/ce-382-brain-drift-local-reconcile.md
.ce/reference/cli.generated.md
validators/creator_engine_validator/carrier_gen.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/integration/test_ce_brain_cli.py
validators/tests/unit/test_carrier_gen.py
validators/tests/unit/test_pr_preflight.py
```
