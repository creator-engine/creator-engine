# PR path manifest — ce-ops#25 · CE version surface

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce25-ce-version-surface` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=9b816de492c9e9bfde28f8cc5d7e1bcfe333969cfddf7178534b7030248ef333

```text
.ce/changelog/ce25-ce-version-surface.md
.ce/pr-manifests/ce25-ce-version-surface.md
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_v3_cli.py
```
