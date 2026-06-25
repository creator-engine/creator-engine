# PR path manifest - lane-0-preflight - Lane 0 PR preflight

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs
`verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref dev4-night-lane0-pr-preflight`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=9870fcbda89f57ecc88d29119e485b801b0454990d1c32e1bab1405717176356

```text
.ce/changelog/dev4-night-lane0-pr-preflight.md
.ce/pr-manifests/dev4-night-lane0-pr-preflight.md
docs/contracts/authoring-a-governed-pr.md
scripts/ce-preflight.sh
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_validate_pr_cli.py
validators/tests/unit/test_pr_preflight.py
```
