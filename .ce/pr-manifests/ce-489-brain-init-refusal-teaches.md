# PR path manifest — ce-ops#489 · Brain init refusal teaches

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-489-brain-init-refusal-teaches` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=af40f29a6c4eceeb68c8cdeea797918cc53da76154c2656a099da7fb3afbe8f7

```text
.ce/changelog/ce-489-brain-init-refusal-teaches.md
.ce/pr-manifests/ce-489-brain-init-refusal-teaches.md
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/onboard_apply.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_v3_cli.py
```
