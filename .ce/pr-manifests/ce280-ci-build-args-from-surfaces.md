# PR path manifest - ce-ops#280 - CI build args from surfaces

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce280-ci-build-args-from-surfaces
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below.
This carrier lists itself.

- **Declared work class:** story

Scope: ce-ops#280 - wire Docker image build inputs to the rented-surface
manifest renderer introduced by ce-ops#279. The validator consistency check is
updated narrowly so the existing manifest consistency gate accepts templated
Dockerfile `FROM` pins that are backed by rendered manifest args.

Per-file purpose:
- **`.ce/changelog/ce280-ci-build-args-from-surfaces.md`** *(A)* - changelog fragment with `work_class: story`.
- **`.ce/pr-manifests/ce280-ci-build-args-from-surfaces.md`** *(A)* - this carrier (self-inclusive).
- **`deploy/oci/build-image.sh`** *(M)* - argv-safe inclusion of rendered surface build args before Docker build.
- **`deploy/oci/Dockerfile`** *(M)* - manifest-controlled CPython base image args default to `UNSET`.
- **`deploy/vps-runsc/Dockerfile`** *(M)* - manifest-controlled CPython, Rust, Debian, herdr, and Zig args default to `UNSET`.
- **`deploy/vps-runsc/README.md`** *(M)* - publish the wrapper build path instead of plain `docker build`.
- **`deploy/vps-runsc/build-image.sh`** *(A)* - supported VPS image build wrapper with rendered surface args.
- **`deploy/dgx-runsc/Dockerfile`** *(M)* - manifest-controlled Rust, Debian, herdr, and Zig args default to `UNSET`.
- **`deploy/dgx-runsc/README.md`** *(M)* - publish the wrapper build path instead of plain `docker build`.
- **`deploy/dgx-runsc/build-image.sh`** *(A)* - supported DGX image build wrapper with rendered surface args.
- **`deploy/dgx-controller-runsc/Dockerfile`** *(M)* - manifest-controlled Rust, Debian, herdr, and Zig args default to `UNSET`.
- **`deploy/dgx-controller-runsc/README.md`** *(M)* - publish the wrapper build path instead of plain `docker build`.
- **`deploy/dgx-controller-runsc/build-image.sh`** *(A)* - supported DGX controller image build wrapper with rendered surface args.
- **`surfaces/render.py`** *(M)* - build-arg rendering emits Docker source/version/digest parts suitable for Dockerfile composition.
- **`validators/creator_engine_validator/checks/surfaces_manifest.py`** *(M)* - consistency gate recognizes templated `FROM` refs backed by manifest args.
- **`validators/tests/unit/test_dgx_controller_runsc.py`** *(M)* - controller Dockerfile assertions for manifest-backed args.
- **`validators/tests/unit/test_dgx_runsc.py`** *(M)* - DGX Dockerfile assertions for manifest-backed args.
- **`validators/tests/unit/test_oci_image.py`** *(M)* - OCI Dockerfile/build-script assertions for rendered surface args.
- **`validators/tests/unit/test_surface_build_wiring.py`** *(A)* - focused wiring tests for CI dry-run, OCI dry-run, and Dockerfile sentinels.
- **`validators/tests/unit/test_surfaces_render.py`** *(M)* - renderer expectation for Docker image build-arg source/digest normalization.
- **`validators/tests/unit/test_vps_runsc_image.py`** *(M)* - VPS Dockerfile assertions for manifest-backed args.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=21

AUTHORIZED_PATHS_SHA256=204d55b38642c191679d16d70bd5141e2314f39f997e17f38566a2ddb3b9b5e1

```text
.ce/changelog/ce280-ci-build-args-from-surfaces.md
.ce/pr-manifests/ce280-ci-build-args-from-surfaces.md
deploy/dgx-controller-runsc/Dockerfile
deploy/dgx-controller-runsc/README.md
deploy/dgx-controller-runsc/build-image.sh
deploy/dgx-runsc/Dockerfile
deploy/dgx-runsc/README.md
deploy/dgx-runsc/build-image.sh
deploy/oci/Dockerfile
deploy/oci/build-image.sh
deploy/vps-runsc/Dockerfile
deploy/vps-runsc/README.md
deploy/vps-runsc/build-image.sh
surfaces/render.py
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_dgx_controller_runsc.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_oci_image.py
validators/tests/unit/test_surface_build_wiring.py
validators/tests/unit/test_surfaces_render.py
validators/tests/unit/test_vps_runsc_image.py
```
