# PR path manifest — ce-ops#445 · offline setuptools for canonical-image wheel builders

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-445-g8-dockerfile-offline-setuptools` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=132415ae37c44e5b42c112967a3315cf1563087f6bdefb77d896a8dcdae0f2b5

```text
.ce/changelog/ce-445-g8-dockerfile-offline-setuptools.md
.ce/pr-manifests/ce-445-g8-dockerfile-offline-setuptools.md
deploy/oci/Dockerfile
deploy/runtime-image/Dockerfile
validators/tests/unit/test_oci_image.py
validators/tests/unit/test_runtime_image.py
```
