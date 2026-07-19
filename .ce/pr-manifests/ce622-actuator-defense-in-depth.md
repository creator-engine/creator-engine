# PR path manifest - actuator defense in depth

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce622-actuator-defense-in-depth` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** S

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=48770efd0effec6936bf398bde55195f8ecb072f3f8d14f64ce8a896246b13a1

```text
.ce/changelog/ce622-actuator-defense-in-depth.md
.ce/pr-manifests/ce622-actuator-defense-in-depth.md
docs/decisions/ADR-0016-pre-delegated-merge-classes.md
validators/creator_engine_validator/forge/automerge_actuator.py
validators/tests/unit/test_automerge_actuator.py
```
