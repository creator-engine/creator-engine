# PR path manifest — ce-ops#488 · Memory-layer slice 1

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-488-memory-layer-slice1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=d8f42505cf0c9ed910d9373ba286eadb8ed00e024e08c861dc2d28ef4995d6ce

```text
.ce/changelog/ce-488-memory-layer-slice1.md
.ce/evidence/ce-488-memory-layer-slice1-remediation.md
.ce/pr-manifests/ce-488-memory-layer-slice1.md
.ce/reference/cli.generated.md
.ce/reference/schemas.generated.md
validators/creator_engine_validator/brain_append_intent.schema.yaml
validators/creator_engine_validator/brain_append_worker.py
validators/creator_engine_validator/brain_runtime.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/schemas/brain-assertion.schema.yaml
validators/creator_engine_validator/takeover_runtime.py
validators/tests/integration/test_ce_brain_cli.py
validators/tests/unit/test_brain_append_worker.py
validators/tests/unit/test_brain_runtime.py
validators/tests/unit/test_ce_takeover_cli.py
```
