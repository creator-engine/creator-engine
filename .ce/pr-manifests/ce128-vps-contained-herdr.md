# PR path manifest - ce128-vps-contained-herdr

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce128-vps-contained-herdr
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`origin/main` after the contained-launch seam batch landed.

- **Declared work class:** story

Scope:
ce-ops#128 VPS contained+herdr recipe for x86_64 Codex and controller seats.
This adds a separate `deploy/vps-runsc/` recipe and does not modify the DGX
recipe while the DGX U-LAUNCHER fix is in flight.

Per-file purpose:
- **`.ce/changelog/ce128-vps-contained-herdr.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce128-vps-contained-herdr.md`** *(A)* - this closed path-set carrier.
- **`deploy/vps-runsc/Dockerfile`** *(A)* - x86_64 runsc image that builds herdr-ce from source and bakes the fail-closed harness entrypoint.
- **`deploy/vps-runsc/README.md`** *(A)* - VPS build, launch, runtime, dry-run, and network caveat notes.
- **`deploy/vps-runsc/herdr-harness-entrypoint.sh`** *(A)* - contained herdr substrate entrypoint with socket-carrier scrubbing.
- **`deploy/vps-runsc/run-vps-runsc.sh`** *(A)* - x86_64 Codex/controller launcher rendering the gVisor Docker argv.
- **`validators/tests/unit/test_vps_runsc_image.py`** *(A)* - static image and entrypoint contract coverage.
- **`validators/tests/unit/test_vps_runsc_launcher.py`** *(A)* - dry-run launcher argv and socket-boundary coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=98a2c56fb642b96a74a558ebebd6404d935bd43c2e7f4c6917ada9fac9a8980c

```text
.ce/changelog/ce128-vps-contained-herdr.md
.ce/pr-manifests/ce128-vps-contained-herdr.md
deploy/vps-runsc/Dockerfile
deploy/vps-runsc/README.md
deploy/vps-runsc/herdr-harness-entrypoint.sh
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/unit/test_vps_runsc_image.py
validators/tests/unit/test_vps_runsc_launcher.py
```
