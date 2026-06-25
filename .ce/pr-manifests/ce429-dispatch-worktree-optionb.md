# PR path manifest — ce-ops#200 · dispatch_worktree Option B

This per-PR carrier lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce429-dispatch-worktree-optionb` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=7cae299ebf137c1eabc8226f2e07f5799a9fa2a46e5a0e3d4f1d6d33a17d3d2f

```text
.ce/changelog/ce429-dispatch-worktree-optionb.md
.ce/pr-manifests/ce429-dispatch-worktree-optionb.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/dispatch_worktree.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_dispatch_worktree.py
validators/tests/unit/test_v3_seat_bridge.py
```
