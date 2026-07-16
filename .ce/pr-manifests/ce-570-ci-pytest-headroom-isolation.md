# PR path manifest — ce-ops#570 · CI pytest headroom isolation

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-570-ci-pytest-headroom-isolation` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=d41c9d0f76595a4442e624792ecb64c3d627e4faefb51acf3adfd80f51626a50

```text
.ce/changelog/ce-570-ci-pytest-headroom-isolation.md
.ce/pr-manifests/ce-570-ci-pytest-headroom-isolation.md
.github/workflows/validate.yml
validators/tests/unit/test_disk_headroom.py
```
