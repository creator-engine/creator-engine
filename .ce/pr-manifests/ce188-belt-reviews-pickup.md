# PR path manifest — ce-ops#188 · belt reviews-pickup — route awaiting-review PRs to non-author seats

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce188-belt-reviews-pickup` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=355cbdad8e8d1b0570397aa1b29f4b6d980c3acdc41ed274b05d868e6134ea74

```text
.ce/changelog/ce188-belt-reviews-pickup.md
.ce/pr-manifests/ce188-belt-reviews-pickup.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pickup.py
validators/tests/unit/test_pickup.py
```
