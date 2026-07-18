# PR path manifest — ce-ops#532 · test(containers): guard contained model canon coherence

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-532-contained-model-canon-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=260ac1d3ff82a0297ac1e0f6902b901e0595a2854dd0c90eeaa0281433791548

```text
.ce/changelog/ce-532-contained-model-canon-guard.md
.ce/pr-manifests/ce-532-contained-model-canon-guard.md
validators/tests/unit/test_contained_model_canon.py
```
