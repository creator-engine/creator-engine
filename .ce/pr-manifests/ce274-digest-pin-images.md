---
slug: ce274-digest-pin-images
date: 2026-06-26
kind: story
scope: [deploy/vps-runsc/Dockerfile, deploy/dgx-runsc/Dockerfile, deploy/dgx-controller-runsc/Dockerfile, deploy/oci/Dockerfile, surfaces/manifest.yaml]
issue: ce-ops#274
---

- **Declared work class:** story

Closes ce-ops#274

This PR pins Docker base images in the runsc and OCI Dockerfiles and records
the matching docker-base-image digests in `surfaces/manifest.yaml`.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=15cb424e7cc2a5ef0d36cb300ad96444cd8967ac8433e4e8dc86b077578d7d76

```text
.ce/changelog/ce274-digest-pin-images.md
.ce/pr-manifests/ce274-digest-pin-images.md
deploy/dgx-controller-runsc/Dockerfile
deploy/dgx-runsc/Dockerfile
deploy/oci/Dockerfile
deploy/vps-runsc/Dockerfile
surfaces/manifest.yaml
```
