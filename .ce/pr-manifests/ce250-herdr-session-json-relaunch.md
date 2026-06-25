# PR path manifest — ce-ops#250 · Clear stale herdr session on contained relaunch

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce250-herdr-session-json-relaunch` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=0d83257c074f7520c66a5a11582fed6e8f457b2f7b6115ffcd0e02b5458cbbda

```text
.ce/changelog/ce250-herdr-session-json-relaunch.md
.ce/pr-manifests/ce250-herdr-session-json-relaunch.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_vps_runsc_launcher.py
```
