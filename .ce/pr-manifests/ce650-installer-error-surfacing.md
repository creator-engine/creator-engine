# PR path manifest — Installer error surfacing

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce650-installer-error-surfacing` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=2ea0f9d1ebc22d0b5d2d335d7f1ab1cd008465aa2c03eb1788cb571cd26cf6d3

```text
.ce/changelog/ce650-installer-error-surfacing.md
.ce/pr-manifests/ce650-installer-error-surfacing.md
validators/creator_engine_validator/main_head_install.py
validators/creator_engine_validator/update.py
validators/creator_engine_validator/venv_install_common.py
validators/tests/unit/test_ce_update.py
validators/tests/unit/test_main_head_install.py
validators/tests/unit/test_venv_install_common.py
```
