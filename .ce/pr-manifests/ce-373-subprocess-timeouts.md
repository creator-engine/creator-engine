# PR path manifest — ce-ops#373 · Bound validate-pr network subprocess calls

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-373-subprocess-timeouts` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=d338134ca317cc52eb8038ba035fa198ecc30ecf3ef96e4b786e9d74504fec4f

```text
.ce/changelog/ce-373-subprocess-timeouts.md
.ce/pr-manifests/ce-373-subprocess-timeouts.md
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_pr_preflight.py
```
