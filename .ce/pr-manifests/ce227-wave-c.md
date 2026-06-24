# PR path manifest — 227 · Wave-C — canary-blocker fixes

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce227-wave-c` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=13

AUTHORIZED_PATHS_SHA256=2b370ba3ef78d67ee47365d6344ca6c9f85cbad33182ecfac010c9b12e2aefa2

```text
.ce/changelog/ce227-wave-c.md
.ce/pr-manifests/ce227-wave-c.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/run-vps-runsc.sh
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/runner/herdr_session.py
validators/creator_engine_validator/seat_class.py
validators/tests/unit/test_codex_pretooluse.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_herdr_session.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_vps_runsc_launcher.py
```
