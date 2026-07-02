# PR path manifest — ce-390 · Extend confidentiality scanner coverage to tracked text files

- **Declared work class:** M

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-390-confidentiality-scanner-coverage` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=55831b98941d858a6a11a28fcb4568550fd29eafe823a45208da31c1d14c4d09

```text
.ce/changelog/ce-390-confidentiality-scanner-coverage.md
.ce/pr-manifests/ce-390-confidentiality-scanner-coverage.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_public_docs_confidentiality.py
validators/tests/unit/test_public_docs_confidentiality_cli.py
```
