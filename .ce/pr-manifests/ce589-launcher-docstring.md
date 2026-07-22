# PR path manifest — ce-ops#589 · Correct governed worker launcher docstring

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce589-launcher-docstring` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=3c7f1ed38e8b90a7a5fc263f926761288839696bed93b08eac29a8d96f064ae8

```text
.ce/changelog/ce589-launcher-docstring.md
.ce/pr-manifests/ce589-launcher-docstring.md
validators/creator_engine_validator/codex_worker_launcher.py
```
