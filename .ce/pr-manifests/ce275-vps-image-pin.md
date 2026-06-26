# PR path manifest - ce275-vps-image-pin

Issue: ce-ops#275
Kind: story

## Scope

- **`.ce/changelog/ce275-vps-image-pin.md`** *(A)* - changelog fragment for the VPS image digest pin.
- **`.ce/pr-manifests/ce275-vps-image-pin.md`** *(A)* - this closed path-set carrier.
- **`deploy/vps-runsc/run-vps-runsc.sh`** *(M)* - pins the default VPS runsc image tag to a sha256 digest and updates help text.
- **`surfaces/manifest.yaml`** *(M)* - records the rented VPS runsc image surface with the same digest.

## Authorized paths

AUTHORIZED_PATHS_COUNT=4
AUTHORIZED_PATHS_SHA256=c41653b7a791a861392ae72bed7fe5ebdca26d3861b138041bc14ac29777ea2b

```text
.ce/changelog/ce275-vps-image-pin.md
.ce/pr-manifests/ce275-vps-image-pin.md
deploy/vps-runsc/run-vps-runsc.sh
surfaces/manifest.yaml
```
