# PR path manifest — ce-ops#370 · Local validate-pr honors PR body test-coupling exemptions

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-370-local-preflight-pr-body` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=57b62ccfd1ada45e42dffee89a56be2e6f4f91295138de62b4ba33691c0a8e17

```text
.ce/changelog/ce-370-local-preflight-pr-body.md
.ce/pr-manifests/ce-370-local-preflight-pr-body.md
.ce/reference/cli.generated.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_validate_pr_cli.py
validators/tests/unit/test_pr_preflight.py
```
