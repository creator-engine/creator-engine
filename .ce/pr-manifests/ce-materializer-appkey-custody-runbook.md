# PR path manifest — materializer App-key custody runbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI verifies that the `base..HEAD` diff equals
exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=e27a61022a6bd5d0f4fce9335224a27f398ebeb9d0cbb69b004465e7630a04d4

```text
.ce/changelog/ce-materializer-appkey-custody-runbook.md
.ce/pr-manifests/ce-materializer-appkey-custody-runbook.md
docs/operations/MATERIALIZER_APPKEY_CUSTODY_RUNBOOK.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_public_docs_confidentiality.py
```
