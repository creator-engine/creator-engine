---
slug: ce274-digest-pin-images
date: 2026-06-26
kind: story
scope: [deploy/vps-runsc/Dockerfile, deploy/dgx-runsc/Dockerfile, deploy/dgx-controller-runsc/Dockerfile, deploy/oci/Dockerfile, surfaces/manifest.yaml, validators/tests/unit/test_dgx_controller_runsc.py, validators/tests/unit/test_dgx_runsc.py, validators/tests/unit/test_vps_runsc_image.py]
issue: ce-ops#274
---

- **Declared work class:** story

Closes ce-ops#274

This PR pins Docker base images in the runsc and OCI Dockerfiles and records
the matching docker-base-image digests in `surfaces/manifest.yaml`.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=f45a02f0f4e1812d741d367195a2218488f6d28186e21564f9b0c909a058b78d

```text
.ce/changelog/ce274-digest-pin-images.md
.ce/pr-manifests/ce274-digest-pin-images.md
deploy/dgx-controller-runsc/Dockerfile
deploy/dgx-runsc/Dockerfile
deploy/oci/Dockerfile
deploy/vps-runsc/Dockerfile
surfaces/manifest.yaml
validators/tests/unit/test_dgx_controller_runsc.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_vps_runsc_image.py
```
