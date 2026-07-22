# PR path manifest — #591 · Tighten VPS static image-contract assertions

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce591-dockerfile-assertion-tightening` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=bef860138cde8671a5fb8d948e19a7aaff0a2ab3e8525d5870803f120fcb8e23

```text
.ce/changelog/ce591-dockerfile-assertion-tightening.md
.ce/pr-manifests/ce591-dockerfile-assertion-tightening.md
validators/tests/unit/test_oci_image.py
validators/tests/unit/test_runtime_image.py
validators/tests/unit/test_seat_image.py
validators/tests/unit/test_vps_runsc_image.py
```
