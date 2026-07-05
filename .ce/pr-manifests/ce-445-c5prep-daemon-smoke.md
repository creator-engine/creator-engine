# PR path manifest - ce-445-c5prep-daemon-smoke

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-445-c5prep-daemon-smoke` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=fcc2c4dc623d1302965c72df659691c8e8ab1232ba14700dcff70a873f238d4e

```text
.ce/changelog/ce-445-c5prep-daemon-smoke.md
.ce/pr-manifests/ce-445-c5prep-daemon-smoke.md
deploy/daemons/README.md
deploy/daemons/smoke-daemon-container.sh
deploy/runtime-image/Dockerfile
validators/tests/unit/test_daemon_container_smoke.py
validators/tests/unit/test_daemon_lease.py
validators/tests/unit/test_oci_image.py
validators/tests/unit/test_runtime_image.py
```
