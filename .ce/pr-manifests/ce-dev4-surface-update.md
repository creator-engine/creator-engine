# PR path manifest — ce-ops#377 · DGX seat image: openssh-client + PyNaCl; codex 0.142.4

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-dev4-surface-update` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=240be097ca3f060c72bf3057719f5e5226bbfc2182da623a655d9f2eb5551c78

```text
.ce/changelog/ce-dev4-surface-update.md
.ce/pr-manifests/ce-dev4-surface-update.md
deploy/dgx-runsc/Dockerfile
deploy/dgx-runsc/build-image.sh
deploy/dgx-runsc/run-codex-runsc.sh
surfaces/manifest.yaml
validators/tests/unit/test_surface_build_wiring.py
```
