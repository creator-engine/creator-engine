# PR path manifest — ce-ops#232 · host-persistent contained-seat logging

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-ops-232-host-persistent-seat-logging-pr` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=488805b53ac41665d265c92df3e4394cf414297293ea80b5b26719f660c9b4e8

```text
.ce/changelog/ce-ops-232-host-persistent-seat-logging-pr.md
.ce/pr-manifests/ce-ops-232-host-persistent-seat-logging-pr.md
deploy/dgx-runsc/herdr-harness-entrypoint.sh
deploy/dgx-runsc/run-codex-runsc.sh
deploy/dgx-runsc/test-seat-logging.sh
deploy/vps-runsc/herdr-harness-entrypoint.sh
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_vps_runsc_image.py
validators/tests/unit/test_vps_runsc_launcher.py
```
