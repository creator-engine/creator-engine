# PR path manifest — ce-ops#494 · onboard workflow refresh

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-494-onboard-workflow-refresh` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=5475f6d6f07b51bbba9a2f5314f63a3249712ab5eb8678c42ac9150d3f2317b5

```text
.ce/changelog/ce-494-onboard-workflow-refresh.md
.ce/pr-manifests/ce-494-onboard-workflow-refresh.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_onboard_apply.py
```
