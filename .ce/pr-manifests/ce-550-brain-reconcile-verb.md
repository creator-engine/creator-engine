# PR path manifest — ce-ops#550 · brain reconcile verb

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-550-brain-reconcile-verb` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=745f400ff66ec677b0272a1aac6d337deaf46c459ff9c4a9d70be89598002e0d

```text
.ce/changelog/ce-550-brain-reconcile-verb.md
.ce/pr-manifests/ce-550-brain-reconcile-verb.md
.ce/reference/cli.generated.md
docs/reference/cli.md
validators/creator_engine_validator/brain_reconcile.py
validators/creator_engine_validator/ce_cli.py
validators/tests/integration/test_ce_brain_cli.py
validators/tests/unit/test_brain_reconcile.py
```
