# PR path manifest - ce-382 brain-drift false-RED

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-382-brain-drift-falsered` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=f163f30fc2d6ef1f5a4c366d09018ca80d3ee9b6b13e9e4de14fd4fcff3729af

```text
.ce/changelog/ce-382-brain-drift-falsered.md
.ce/pr-manifests/ce-382-brain-drift-falsered.md
validators/creator_engine_validator/checks/ce_brain_drift.py
validators/tests/unit/test_ce_brain_drift.py
```
