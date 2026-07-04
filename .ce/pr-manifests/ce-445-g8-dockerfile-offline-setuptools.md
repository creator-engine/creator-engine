# PR path manifest — ce-ops#445 · offline setuptools for canonical-image wheel builders

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-445-g8-dockerfile-offline-setuptools` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=f6fe81ab9c09858a53c006e4ac2561c5b9566eb24d14822d3b38a7c774aa2a3d

```text
.ce/changelog/ce-445-g8-dockerfile-offline-setuptools.md
.ce/pr-manifests/ce-445-g8-dockerfile-offline-setuptools.md
deploy/oci/Dockerfile
deploy/oci/build-image.sh
deploy/runtime-image/Dockerfile
validators/tests/unit/test_oci_image.py
validators/tests/unit/test_runtime_image.py
```
