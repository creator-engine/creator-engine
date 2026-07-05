# PR path manifest — 431 · ce launch --preflight gate-diagnostic mode

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-431-launch-preflight-diagnostic` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=826481f4ab2e04103c0e76b3abf8fb4a0b21bc2ee74b3a558f4f815e5378da98

```text
.ce/changelog/ce-431-launch-preflight-diagnostic.md
.ce/pr-manifests/ce-431-launch-preflight-diagnostic.md
.ce/reference/cli.generated.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/launch_runtime.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_launch_runtime_resource_bound.py
```
