# PR path manifest — ce-ops#208 · OCI image for CE CLI and validator

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce208-oci-image` and requires this
PR's `base..HEAD` diff to equal exactly the authorized path-set below; this
carrier lists itself.

- **Declared work class:** feature

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=609c4938c048209b9859c98502072d5efdeb4a70d86c4af9912355c020f9a872

```text
.ce/changelog/ce208-oci-image.md
.ce/pr-manifests/ce208-oci-image.md
deploy/dgx-runsc/README.md
deploy/oci/Dockerfile
deploy/oci/README.md
deploy/oci/build-image.sh
deploy/vps-runsc/README.md
validators/tests/unit/test_oci_image.py
```
