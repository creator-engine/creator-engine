# PR path manifest — ce-ops#377 · per-arch base-image digests

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-377-per-arch-base-digests` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=4b2a63978a14fd41c6912405ba8122d5567fa41225ae75e520060a73627a6360

```text
.ce/changelog/ce-377-per-arch-base-digests.md
.ce/pr-manifests/ce-377-per-arch-base-digests.md
deploy/dgx-controller-runsc/build-image.sh
deploy/dgx-runsc/build-image.sh
deploy/vps-runsc/build-image.sh
surfaces/manifest.yaml
surfaces/render.py
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_surface_build_wiring.py
validators/tests/unit/test_surfaces_manifest.py
validators/tests/unit/test_surfaces_render.py
```
