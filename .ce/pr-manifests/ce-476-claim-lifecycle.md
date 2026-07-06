# PR path manifest — ce-ops#476 · work_claims lifecycle seed slice

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-476-claim-lifecycle` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=cdf50a747a3cd4dc51300c3648be9df4b4f6fec93158ae8339b5acf19e01e6e4

```text
.ce/changelog/ce-476-claim-lifecycle.md
.ce/pr-manifests/ce-476-claim-lifecycle.md
.github/workflows/ce-claim-closeout.yml
docs/claims-lifecycle.md
validators/claim_lifecycle.py
validators/creator_engine_validator/ce_cli.py
validators/tests/unit/test_ce_claim_closeout_workflow.py
validators/tests/unit/test_ce_claim_lifecycle_cli.py
validators/tests/unit/test_claim_lifecycle.py
```
