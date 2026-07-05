# PR path manifest — live-canary · Fix npm profile PATH discovery

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-npm-path-fix` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=60919e71a47b4ae41b09c80b6873d999beab92b998fce901ea9f24a7b379288c

```text
.ce/changelog/ce-npm-path-fix.md
.ce/pr-manifests/ce-npm-path-fix.md
validators/creator_engine_validator/ce_profile_path.py
validators/tests/unit/test_ce_profile_path.py
```
