# PR path manifest — ce-ops#207 · headless/non-tmux visibility backend for lane launch

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce207-visibility-backend` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=b4b81bf69fe3273d49cfaca16a0f1005f14ddc7293be7461cd3e1e6ae55fa438

```text
.ce/changelog/ce207-visibility-backend.md
.ce/pr-manifests/ce207-visibility-backend.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/visibility_backend.py
validators/tests/integration/test_v1_delivery_rehearsal.py
validators/tests/unit/test_ce_lane_cli.py
validators/tests/unit/test_lane_runtime.py
validators/tests/unit/test_visibility_backend.py
```
