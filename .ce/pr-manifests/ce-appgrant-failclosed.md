# PR path manifest — 88 · fail-closed App-grant minimum

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-appgrant-failclosed` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=2fa4c6bdaee3d88e11f8c81e163be4052d77f283f1f6baa5a4042131d6ca25c6

```text
.ce/changelog/ce-appgrant-failclosed.md
.ce/pr-manifests/ce-appgrant-failclosed.md
tools/mint-broker/mint_broker/config.py
tools/mint-broker/mint_broker/service.py
validators/tests/unit/test_mint_broker_config.py
validators/tests/unit/test_mint_broker_service.py
```
