# PR path manifest — ce-ops#616 · Orchestrator runtime-record schemas

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-orchestrator-record-schemas` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** feature

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=6586ad25c44043e1a53e712bb9a345b401dd236ff2a4a49da0e17dd5980754b4

```text
.ce/changelog/ce-orchestrator-record-schemas.md
.ce/pr-manifests/ce-orchestrator-record-schemas.md
.ce/reference/schemas.generated.md
validators/creator_engine_validator/orchestrator_records.py
validators/creator_engine_validator/schemas/orchestrator-checkpoint.schema.yaml
validators/creator_engine_validator/schemas/orchestrator-harvest-packet.schema.yaml
validators/creator_engine_validator/schemas/orchestrator-operator-decision.schema.yaml
validators/creator_engine_validator/schemas/orchestrator-territory-map.schema.yaml
validators/tests/unit/test_orchestrator_records.py
```
