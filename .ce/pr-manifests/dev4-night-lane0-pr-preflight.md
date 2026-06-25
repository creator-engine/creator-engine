# PR path manifest — ce-ops#252 · Lane 0 governed PR preflight

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref dev4-night-lane0-pr-preflight` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=ae03da7c8f8681cdcfd8919b2fa808646a6a11d94e793e01fba56584720e1ae7

```text
.ce/changelog/dev4-night-lane0-pr-preflight.md
.ce/pr-manifests/dev4-night-lane0-pr-preflight.md
README.md
docs/contracts/authoring-a-governed-pr.md
scripts/ce-preflight.sh
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_validate_pr_cli.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
