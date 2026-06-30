# PR path manifest — ce-ops#371 · Auto-update P0 startup notice

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-371-autoupdate-p0-startup-notice` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=bb5382d5a2543d394e29a7983f6ed44685d036a7ce0f346c9877d3915dff4821

```text
.ce/changelog/ce-371-autoupdate-p0-startup-notice.md
.ce/pr-manifests/ce-371-autoupdate-p0-startup-notice.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/update.py
validators/tests/unit/test_ce_update.py
validators/tests/unit/test_hook_check.py
```
