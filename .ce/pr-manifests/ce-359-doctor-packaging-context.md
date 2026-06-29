# PR path manifest — ce-ops#359 · Gate doctor packaging checks to CE source-tree context

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-359-doctor-packaging-context` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=1a17aa9d68ffbe09e56aab3503e26ae2c938a7f7c8abbd1dad6f228b0d740406

```text
.ce/changelog/ce-359-doctor-packaging-context.md
.ce/pr-manifests/ce-359-doctor-packaging-context.md
validators/creator_engine_validator/doctor_runtime.py
validators/creator_engine_validator/environment_guard.py
validators/tests/integration/test_ce_doctor_cli.py
validators/tests/unit/test_ce_onboard.py
validators/tests/unit/test_environment_guard.py
```
