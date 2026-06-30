# PR path manifest — ce-ops#377 · DGX seat image: openssh-client + PyNaCl; codex 0.142.4

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-dev4-surface-update` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=a7da1bd34a7c552dd731151833994e351751c7fa212fea7a2bf7214ac7ac3a75

```text
.ce/changelog/ce-dev4-surface-update.md
.ce/pr-manifests/ce-dev4-surface-update.md
deploy/dgx-runsc/Dockerfile
deploy/dgx-runsc/build-image.sh
deploy/dgx-runsc/run-codex-runsc.sh
surfaces/manifest.yaml
```
