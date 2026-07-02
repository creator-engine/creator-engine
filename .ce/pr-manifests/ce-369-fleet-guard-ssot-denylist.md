# PR path manifest — ce-ops#369 · Fleet manifest guard uses identity registry denylist snapshot

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-369-fleet-guard-ssot-denylist` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=b6b6979619a172854163b3ce639e4b950baebf66b6430180fd8362652158df34

```text
.ce/changelog/ce-369-fleet-guard-ssot-denylist.md
.ce/pr-manifests/ce-369-fleet-guard-ssot-denylist.md
validators/creator_engine_validator/checks/fleet_manifest_guard.py
validators/creator_engine_validator/fleet_identity_denylist_codegen.py
validators/creator_engine_validator/fleet_identity_denylist_snapshot.py
validators/tests/unit/test_fleet_manifest_guard.py
```
