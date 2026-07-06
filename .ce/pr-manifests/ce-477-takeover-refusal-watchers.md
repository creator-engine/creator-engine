# PR path manifest — ce-ops#477 · Takeover refusal and watcher re-arm

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-477-takeover-refusal-watchers` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=1beda34e89a2eee0fe8c4f42d763a9fcaf8297d0d08531ec1a2a400047a53b44

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-477-takeover-refusal-watchers.md
.ce/pr-manifests/ce-477-takeover-refusal-watchers.md
.ce/reference/cli.generated.md
docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/takeover_runtime.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_ce_takeover_cli.py
```
