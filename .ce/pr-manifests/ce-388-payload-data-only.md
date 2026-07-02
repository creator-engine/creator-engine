# PR path manifest — ce-ops#388 · Wire ADR-0004 payload schema into conveyor daemon discovery

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-388-payload-data-only` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=557adcecd980da82b0099067d9c09aaa6f631edbf3902aee72362090c9191ad0

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-388-payload-data-only.md
.ce/pr-manifests/ce-388-payload-data-only.md
validators/creator_engine_validator/conveyor_daemon.py
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/pickup.py
validators/creator_engine_validator/pickup_payload_schema.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_conveyor_daemon.py
validators/tests/unit/test_pickup_payload_schema.py
```
