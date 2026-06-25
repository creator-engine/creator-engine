# PR path manifest — ce-ops#244 · default codex TUI statusline for contained CE seats

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-codex-statusline-default` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=fe270bafe96e9194c8180767b1ecb00a6b9c24bf731261ecd441c6f0bbca2a47

```text
.ce/changelog/ce-codex-statusline-default.md
.ce/pr-manifests/ce-codex-statusline-default.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_vps_runsc_launcher.py
```
