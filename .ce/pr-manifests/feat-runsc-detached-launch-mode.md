# PR path manifest — ce-ops#408 · detached runsc launch + secret-retention guard

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref feat-runsc-detached-launch-mode` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=5a662898205895372f12d09d2f0339eb99e488a79077c8070adbf54af7d99772

```text
.ce/changelog/feat-runsc-detached-launch-mode.md
.ce/pr-manifests/feat-runsc-detached-launch-mode.md
deploy/dgx-controller-runsc/README.md
deploy/dgx-controller-runsc/run-controller-runsc.sh
deploy/dgx-runsc/README.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/README.md
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/unit/test_dgx_controller_runsc.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_vps_runsc_launcher.py
```
