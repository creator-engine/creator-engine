# PR path manifest — ce-ops#538 · Ship the tenant Claude hook-pack

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-538-hookpack-delivery` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=4df7ef80a4cde4e1ef02fd1c0005c7e9725fe3b0703d0a5dcc1150cb02025503

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-538-hookpack-delivery.md
.ce/pr-manifests/ce-538-hookpack-delivery.md
validators/creator_engine_validator/claude_hook_pack.py
validators/creator_engine_validator/claude_launch_spec.py
validators/creator_engine_validator/hook_pack_assets/ce-hook-common.sh
validators/creator_engine_validator/hook_pack_assets/ce-pretooluse.sh
validators/creator_engine_validator/hook_pack_assets/ce-stop.sh
validators/creator_engine_validator/hook_pack_assets/settings.json
validators/creator_engine_validator/onboard_apply.py
validators/pyproject.toml
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_claude_hook_pack.py
validators/tests/unit/test_claude_launch_spec.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_onboard_apply.py
```
