# PR path manifest — creator-engine/ce-ops#428 · ce check client-repo profile

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-428-client-repo-check-profile` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=6c3d3354c228b7cc9f15eeba816ee5c142567639d7468ba483059ee25271adea

```text
.ce/changelog/ce-428-client-repo-check-profile.md
.ce/pr-manifests/ce-428-client-repo-check-profile.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/check_profiles.py
validators/creator_engine_validator/cli.py
validators/tests/integration/test_ce_check_cli.py
```
