# PR path manifest — ce-ops#250 · Canonical Herdr socket route

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-250-herdr-socket-route` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=afbc4cbce088cd08370698895c42eab485d7b05ea463cf1409be9778c8b234e0

```text
.ce/changelog/ce-250-herdr-socket-route.md
.ce/pr-manifests/ce-250-herdr-socket-route.md
deploy/vps-runsc/Dockerfile
deploy/vps-runsc/README.md
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/unit/test_vps_runsc_image.py
validators/tests/unit/test_vps_runsc_launcher.py
```
