# PR path manifest — ce-ops#488 · Memory-layer slice 1

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-488-memory-layer-slice1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=20a873c46fef826071087fbb0736dabab1401b10782cb9a54e1a16dc00ff4994

```text
.ce/changelog/ce-488-memory-layer-slice1.md
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
