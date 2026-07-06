# PR path manifest - Batch2 B1 - Pin 0.3.3 runtime and seat image digests

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-033-digest-pin` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=39bf76029a6e557aa6674c035af71fc4d2b064c4ff7f0cb345635069e4e91e29

```text
.ce/changelog/ce-033-digest-pin.md
.ce/pr-manifests/ce-033-digest-pin.md
surfaces/manifest.yaml
validators/tests/unit/test_seat_image.py
```
