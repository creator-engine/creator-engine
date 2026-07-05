# PR path manifest — operator-ratified day-arc · Canonical tenant seat image

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-s1b-seat-image` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=ed1d6f968231dae862025dc906b6fcc2d848a9ce1afdd092ba13d1a0f698e9f8

```text
.ce/changelog/ce-s1b-seat-image.md
.ce/pr-manifests/ce-s1b-seat-image.md
.github/workflows/publish-seat-image.yml
deploy/seat-image/Dockerfile
deploy/seat-image/README.md
surfaces/manifest.yaml
validators/tests/unit/test_seat_image.py
```
