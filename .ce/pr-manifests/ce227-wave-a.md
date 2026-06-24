# PR path manifest — 227 · Wave-A — register Ring-1 PreToolUse hook in contained seat config + canary test-hardening

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce227-wave-a` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=736e318865be6ce9dce6f66f5c7eac5cab01e9db19f6dd38da529748a1f4cdc3

```text
.ce/pr-manifests/ce227-wave-a.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/integration/test_herdr_live.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_herdr_session.py
validators/tests/unit/test_vps_runsc_launcher.py
```
