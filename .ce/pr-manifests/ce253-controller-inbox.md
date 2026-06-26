# PR path manifest — ce-ops#253 · Controller awaiting-decision inbox

- **Declared work class:** feature

This per-PR carrier (`.ce/pr-manifests/ce253-controller-inbox.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce253-controller-inbox` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=bcdd22a5f0be8c924b18e0f6640f89e963c09b7bb0a03553e44c3eee50dddfef

```text
.ce/changelog/ce253-controller-inbox.md
.ce/pr-manifests/ce253-controller-inbox.md
validators/creator_engine_validator/forge/controller_inbox.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_controller_inbox.py
```
