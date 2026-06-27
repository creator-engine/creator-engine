# PR path manifest — ce-ops#332 · Robust tmux pane-identity parsing across tab-sanitizing tmux builds

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref fix-ce-ops-332-tmux-identity-parse` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=4aa64cdedc44603a0dbbdced7d4a1fb993a1c8b1e92517e5759b5fd9568a62e8

```text
.ce/changelog/fix-ce-ops-332-tmux-identity-parse.md
.ce/pr-manifests/fix-ce-ops-332-tmux-identity-parse.md
validators/creator_engine_validator/tmux_adapter.py
validators/tests/unit/test_tmux_adapter.py
```
