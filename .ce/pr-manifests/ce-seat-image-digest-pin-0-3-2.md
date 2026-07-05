# PR path manifest — ce-ops#823 · Pin the 0.3.2 tenant seat image manifest-list digest and retire its unset-digest allowlist

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-seat-image-digest-pin-0-3-2` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=5d23be26b4644fea9f3205ce688f8dae0145eb02c38f445b83a3ae3e83735b58

```text
.ce/changelog/ce-seat-image-digest-pin-0-3-2.md
.ce/pr-manifests/ce-seat-image-digest-pin-0-3-2.md
surfaces/manifest.yaml
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_seat_image.py
validators/tests/unit/test_surfaces_manifest.py
```
