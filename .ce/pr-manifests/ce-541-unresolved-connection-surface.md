# PR path manifest — ce-ops#541 · Surface unresolved onboarding connection

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-541-unresolved-connection-surface` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=dacd362fb395288bcf5dcf8e45c386460e65e391cc7e711273b90667f843487d

```text
.ce/changelog/ce-541-unresolved-connection-surface.md
.ce/pr-manifests/ce-541-unresolved-connection-surface.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/doctor_runtime.py
validators/creator_engine_validator/onboard_connection_status.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_ce_doctor_cli.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_onboard_connection_status.py
validators/tests/unit/test_v3_cli.py
```
