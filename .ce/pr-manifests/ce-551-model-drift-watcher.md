# PR path manifest — ce-ops#551 · feat(daemons): add model drift watcher (M9)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-551-model-drift-watcher` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=9126ba63e913ca46c662e4279301aea307a0ac51fc5f959ed514dea99dbb460f

```text
.ce/changelog/ce-551-model-drift-watcher.md
.ce/pr-manifests/ce-551-model-drift-watcher.md
.ce/reference/schemas.generated.md
deploy/systemd/README.md
deploy/systemd/ce-model-drift-watcher.service
deploy/systemd/install-gate-daemons-systemd.sh
surfaces/model-canon.yaml
validators/creator_engine_validator/model_drift_watcher.py
validators/creator_engine_validator/schemas/model-canon.schema.yaml
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_model_drift_watcher.py
```
