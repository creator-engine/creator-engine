# PR path manifest - image daemon deps

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-445-g10-image-daemon-deps` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=768366d51cae8774a161c99ff87ad8d33394ebbdb61b135b47f6523a9fb4f526

```text
.ce/changelog/ce-445-g10-image-daemon-deps.md
.ce/pr-manifests/ce-445-g10-image-daemon-deps.md
deploy/oci/Dockerfile
deploy/runtime-image/Dockerfile
validators/tests/unit/test_oci_image.py
validators/tests/unit/test_runtime_image.py
```
