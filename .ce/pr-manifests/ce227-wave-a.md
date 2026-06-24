# PR path manifest — 227 · Wave-A — register Ring-1 PreToolUse hook in contained seat config + canary test-hardening

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce227-wave-a` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=739b16c0000d5f7c77a2ad1d7e873ede34f4ba2a4b4ce9e49ceb1c0b02859480

```text
.ce/changelog/ce227-wave-a.md
.ce/pr-manifests/ce227-wave-a.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/integration/test_herdr_live.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_herdr_session.py
validators/tests/unit/test_vps_runsc_launcher.py
```
