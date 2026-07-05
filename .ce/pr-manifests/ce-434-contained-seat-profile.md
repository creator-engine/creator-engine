# PR path manifest — ce-434-contained-seat-profile · validate-pr contained-seat profile

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-434-contained-seat-profile` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=3d40ff4c1bee48ab0ce23d7e66a7a9c099d3014c265288d6c57325556d99965e

```text
.ce/changelog/ce-434-contained-seat-profile.md
.ce/pr-manifests/ce-434-contained-seat-profile.md
playbooks/controller/briefs/dispatch.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_validate_pr_cli.py
validators/tests/unit/test_pr_preflight.py
```
