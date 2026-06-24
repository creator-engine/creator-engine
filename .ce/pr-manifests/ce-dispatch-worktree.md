# PR path manifest — ce-ops#200 · collision-safe concurrent dispatch core (dispatch_worktree, v1-classified)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-dispatch-worktree` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=8929c14ded86f19eafbeca63d359fa020b0dde59372c86fc63f137d386cf1aa4

```text
.ce/changelog/ce-dispatch-worktree.md
.ce/pr-manifests/ce-dispatch-worktree.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/dispatch_worktree.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_dispatch_worktree.py
```
