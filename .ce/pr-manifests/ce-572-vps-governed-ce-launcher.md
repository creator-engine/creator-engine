# PR path manifest - ce-572-vps-governed-ce-launcher

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`).

Base:
`5d85bc196c6aa4dd2dcfe190caaffb0ee83121dd`.

- **Declared work class:** story

Scope:
Make the root-owned governed `ce` launcher durable in the VPS runsc image.
This change does not deploy or relaunch a seat.

Per-file purpose:
- **`.ce/changelog/ce-572-vps-governed-ce-launcher.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-572-vps-governed-ce-launcher.md`** *(A)* - this closed path-set carrier.
- **`deploy/vps-runsc/Dockerfile`** *(M)* - install the offline-validator `ce` launcher with root-owned 0755 semantics.
- **`validators/tests/unit/test_vps_runsc_image.py`** *(M)* - pin the launcher interpreter, source path, argument handling, and installation contract.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=1890079b396598e7cce4e321ddd2a335034c807c6edcf9919a4b4b1ac4a79544

```text
.ce/changelog/ce-572-vps-governed-ce-launcher.md
.ce/pr-manifests/ce-572-vps-governed-ce-launcher.md
deploy/vps-runsc/Dockerfile
validators/tests/unit/test_vps_runsc_image.py
```
