# PR path manifest - L2 · Automerge canary live-data decision inputs

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-L2-automerge-canary-livedata` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=5a8d1d7034217b1c25204b3108c15261c62412689d41968f668277a54227eb10

```text
.ce/changelog/ce-l2-automerge-canary-livedata.md
.ce/pr-manifests/ce-l2-automerge-canary-livedata.md
.github/workflows/automerge-decide.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/automerge_actuator.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
validators/tests/unit/test_automerge_status.py
```
