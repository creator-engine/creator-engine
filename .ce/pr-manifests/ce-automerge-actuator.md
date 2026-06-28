# PR path manifest — ce-ops#313 · Forge automerge actuator

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-automerge-actuator` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=29319fcfa3781b85cebb42e4756d4a11da7ff369ff6aecb4604b08b48d918a79

```text
.ce/changelog/ce-automerge-actuator.md
.ce/pr-manifests/ce-automerge-actuator.md
validators/creator_engine_validator/forge/automerge_actuator.py
validators/tests/unit/test_automerge_actuator.py
```
