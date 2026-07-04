# PR path manifest — ce-ops#N5 · Add fail-safe worktree prune tool

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-n5-worktree-prune` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=619ccd7681787c4310c0f8e4dfbdcfb960bdbb14f2da81cccb5f05a12ea5a7ca

```text
.ce/changelog/ce-n5-worktree-prune.md
.ce/pr-manifests/ce-n5-worktree-prune.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/worktree_prune.py
validators/tests/unit/test_worktree_prune.py
```
