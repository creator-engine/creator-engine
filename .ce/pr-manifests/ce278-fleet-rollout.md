# PR path manifest — ce-ops#278 · ce surfaces fleet-rollout

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce278-fleet-rollout
```

- **Declared work class:** Feature

Scope: ce-ops#278 — add `ce surfaces fleet-rollout` subcommand.

Per-file purpose:
- **`.ce/changelog/ce278-fleet-rollout.md`** *(A)* - changelog fragment
- **`.ce/pr-manifests/ce278-fleet-rollout.md`** *(A)* - this carrier (self-inclusive)
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - register fleet-rollout sub-subcommand
- **`validators/creator_engine_validator/surfaces/fleet_rollout.py`** *(A)* - fleet-rollout implementation
- **`validators/tests/unit/test_surfaces_fleet_rollout.py`** *(A)* - unit tests

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=554752eac2e8eed4750bb407015fe77dd255318b8fa38d2f1b6d9e08a1a53af9

```text
.ce/changelog/ce278-fleet-rollout.md
.ce/pr-manifests/ce278-fleet-rollout.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/surfaces/fleet_rollout.py
validators/tests/unit/test_surfaces_fleet_rollout.py
```
