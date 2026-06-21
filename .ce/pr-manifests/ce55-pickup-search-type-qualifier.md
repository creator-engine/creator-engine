# PR path manifest - ce55-pickup-search-type-qualifier

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce55-pickup-search-type-qualifier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path set
below. This carrier lists itself.

Change:
Fixes GitHub Search API pickup polling after Search Issues started requiring
each query to include an explicit type qualifier. Review-request pickup remains
PR-only, while assigned, mention, and label pickup cover both PR and issue
surfaces without broadening repo/org or label scoping.

Per-file purpose (closed path-set - 4 paths):
- **`.ce/changelog/ce55-pickup-search-type-qualifier.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce55-pickup-search-type-qualifier.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/pickup.py`** *(M)* - explicit Search type qualifiers in query construction.
- **`validators/tests/unit/test_pickup.py`** *(M)* - regression coverage requiring typed Search queries.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=b85560354e0c5ec8127663d5a41d47f7fc769f30f7c06337174f289bcaf8a513

```text
.ce/changelog/ce55-pickup-search-type-qualifier.md
.ce/pr-manifests/ce55-pickup-search-type-qualifier.md
validators/creator_engine_validator/pickup.py
validators/tests/unit/test_pickup.py
```
