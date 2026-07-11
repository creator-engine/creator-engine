# PR path manifest — none · Dual-format sibling sync gate

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-n3-dualformat-sync-gate` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=bbbaa0d0f3dc659aab6721bac19e9f57365a50dc79a88ad85d6ad8fe82f6842b

```text
.ce/changelog/ce-n3-dualformat-sync-gate.md
.ce/pr-manifests/ce-n3-dualformat-sync-gate.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/dual_format_sync.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_dual_format_sync.py
```
