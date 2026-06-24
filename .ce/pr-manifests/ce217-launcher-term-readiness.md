# PR path manifest — ce-ops#217 · launcher TERM coercion + readiness-probe hardening

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce217-launcher-term-readiness` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=bbeb859b75bf8127731202ce35d9a4e6ccb484a92f48915d70a7b20d396e25f9

```text
.ce/changelog/ce217-launcher-term-readiness.md
.ce/pr-manifests/ce217-launcher-term-readiness.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/dgx-runsc/test-term-coercion.sh
deploy/vps-runsc/run-vps-runsc.sh
```
