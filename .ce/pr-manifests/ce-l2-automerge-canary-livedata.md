# PR path manifest - L2 · Automerge canary live-data decision inputs

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-L2-automerge-canary-livedata` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=9faed8d8e4318a94c1200a8903bc26b8d400d30ee40d0d69a3572cd6b392f9f2

```text
.ce/changelog/ce-l2-automerge-canary-livedata.md
.ce/pr-manifests/ce-l2-automerge-canary-livedata.md
.ce/reference/cli.generated.md
.github/workflows/automerge-decide.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/automerge_actuator.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
validators/tests/unit/test_automerge_status.py
```
