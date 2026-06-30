# PR path manifest — L7-f · Release finalize integration coverage

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l7f-integration` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=b35b1be103f598830fea813f17fe19cba9e1ef020d3c936753dd59e8025993f7

```text
.ce/changelog/ce-l7f-integration.md
.ce/pr-manifests/ce-l7f-integration.md
validators/tests/integration/test_release_finalize_integration.py
```
