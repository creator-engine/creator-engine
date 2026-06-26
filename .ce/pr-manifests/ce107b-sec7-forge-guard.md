# PR path manifest — ce-ops#107(B) · Section 7 forge guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce107b-sec7-forge-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=024c035ea8982474e51435d0efd62e24988f722cd8c3409411b9d25b9b1abc1d

```text
.ce/changelog/ce107b-sec7-forge-guard.md
.ce/pr-manifests/ce107b-sec7-forge-guard.md
validators/creator_engine_validator/forge/auto_merge.py
validators/creator_engine_validator/forge/github_repo_config.py
validators/creator_engine_validator/forge/review_submit.py
validators/creator_engine_validator/forge/ruleset.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/sec7_forge_guard.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_forge_join.py
validators/tests/unit/test_auto_merge.py
validators/tests/unit/test_github_repo_config.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_review_submit.py
validators/tests/unit/test_ruleset.py
validators/tests/unit/test_v3_forge_join.py
```
