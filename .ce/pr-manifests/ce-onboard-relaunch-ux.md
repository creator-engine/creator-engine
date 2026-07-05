# PR path manifest — ce-ops#447 · onboard relaunch UX

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-onboard-relaunch-ux` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=e507409e7c4564a77819f238b56de0312aa9c29a08d0f26b4b5762a2c5a9f4dd

```text
.ce/changelog/ce-onboard-relaunch-ux.md
.ce/pr-manifests/ce-onboard-relaunch-ux.md
.ce/reference/cli.generated.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/ce_onboard.py
validators/creator_engine_validator/doctor_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/tests/unit/test_ce_doctor_cli.py
validators/tests/unit/test_ce_onboard.py
validators/tests/unit/test_launch_runtime.py
```
