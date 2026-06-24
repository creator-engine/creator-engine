# PR path manifest — ce-ops#200 · Collision-safe concurrent dispatch core

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-dispatch-worktree` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=828dee4d1d0e4c5380bb09f319dad22be839e772695081909b2d8dec8b39244d

```text
.ce/changelog/ce-dispatch-worktree.md
.ce/pr-manifests/ce-dispatch-worktree.md
validators/creator_engine_validator/dispatch_worktree.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_dispatch_worktree.py
```
