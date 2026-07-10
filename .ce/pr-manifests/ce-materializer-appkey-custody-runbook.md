# PR path manifest — materializer App-key custody runbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI verifies that the `base..HEAD` diff equals
exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=6a055dcc3a6fda3d03782811d200eb4cb2d8b1e08e782adf8303250867196172

```text
.ce/changelog/ce-materializer-appkey-custody-runbook.md
.ce/pr-manifests/ce-materializer-appkey-custody-runbook.md
docs/operations/MATERIALIZER_APPKEY_CUSTODY_RUNBOOK.md
validators/creator_engine_validator/public_docs_confidentiality.py
```
