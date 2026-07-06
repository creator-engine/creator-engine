# PR path manifest — ce-ops#458 · Profile-aware list-checks output

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-458-list-checks-profile-ux` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=9f6480fec34e23d099d236f5d2d7c42cfbf60d60521707f18c3a64aa5a87d63c

```text
.ce/changelog/ce-458-list-checks-profile-ux.md
.ce/pr-manifests/ce-458-list-checks-profile-ux.md
validators/creator_engine_validator/cli.py
validators/tests/unit/test_cli.py
```
