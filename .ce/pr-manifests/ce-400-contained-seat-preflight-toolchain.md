# PR path manifest - ce-400 contained seat preflight toolchain

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-400-contained-seat-preflight-toolchain` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=77d99da8f68dfc4c15550e1a01bd91818dec32940ae0e1e5bd52d179363ce1d3

```text
.ce/changelog/ce-400-contained-seat-preflight-toolchain.md
.ce/pr-manifests/ce-400-contained-seat-preflight-toolchain.md
deploy/vps-runsc/Dockerfile
deploy/dgx-runsc/Dockerfile
deploy/oci/Dockerfile
deploy/runtime-image/Dockerfile
deploy/seat-image/Dockerfile
deploy/oci/build-image.sh
validators/tests/unit/test_vps_runsc_image.py
validators/tests/unit/test_oci_image.py
validators/tests/unit/test_runtime_image.py
validators/tests/unit/test_seat_image.py
```
