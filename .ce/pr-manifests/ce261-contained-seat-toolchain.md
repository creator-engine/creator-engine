# ce-ops#261 Contained Seat Toolchain

ticket: ce-ops#261
branch: ce261-contained-seat-toolchain
- **Declared work class:** tiny

files_changed:
- .ce/pr-manifests/ce261-contained-seat-toolchain.md
- .ce/changelog/ce261-contained-seat-toolchain.md
- deploy/dgx-runsc/Dockerfile
- deploy/vps-runsc/Dockerfile

description: Bake the pinned pytest-xdist validator test toolchain into the contained DGX and VPS runsc images and verify xdist flags with an image-build smoke check.

AUTHORIZED_PATHS_COUNT=4
AUTHORIZED_PATHS_SHA256=b0e60843a95580459ea40fd9d45d4772e47c740571a9b860a7c517935d21e2db

```text
.ce/changelog/ce261-contained-seat-toolchain.md
.ce/pr-manifests/ce261-contained-seat-toolchain.md
deploy/dgx-runsc/Dockerfile
deploy/vps-runsc/Dockerfile
```
