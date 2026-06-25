# PR path manifest — ce-ops#232 · persist contained-seat logs to host

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce232-contained-seat-logging` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=3a8014fc5e9768a5fa0570ff6e390f88772a6493cca50d098e95066ef0ac7a37

```text
.ce/changelog/ce232-contained-seat-logging.md
.ce/pr-manifests/ce232-contained-seat-logging.md
deploy/dgx-runsc/herdr-harness-entrypoint.sh
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/herdr-harness-entrypoint.sh
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_vps_runsc_image.py
validators/tests/unit/test_vps_runsc_launcher.py
```
