# PR path manifest - ce275-vps-image-pin

Issue: ce-ops#275
Kind: story

## Scope

- **`.ce/changelog/ce275-vps-image-pin.md`** *(A)* - changelog fragment for the VPS image digest pin.
- **`.ce/pr-manifests/ce275-vps-image-pin.md`** *(A)* - this closed path-set carrier.
- **`deploy/vps-runsc/run-vps-runsc.sh`** *(M)* - pins the default VPS runsc image tag to a sha256 digest and updates help text.
- **`surfaces/manifest.yaml`** *(M)* - records the rented VPS runsc image surface with the same digest.
- **`validators/tests/unit/test_vps_runsc_launcher.py`** *(M)* - accepts the pinned VPS runsc image digest in dry-run argv assertions.

## Authorized paths

AUTHORIZED_PATHS_COUNT=5
AUTHORIZED_PATHS_SHA256=7eb70cf35ac0b1cdd8b28260ba866cff508609871ffe8c8a0ff6c02f673d5a7c

```text
.ce/changelog/ce275-vps-image-pin.md
.ce/pr-manifests/ce275-vps-image-pin.md
deploy/vps-runsc/run-vps-runsc.sh
surfaces/manifest.yaml
validators/tests/unit/test_vps_runsc_launcher.py
```
