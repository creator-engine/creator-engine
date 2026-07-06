# PR path manifest — ce-ops#476 · work_claims lifecycle seed slice

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-476-claim-lifecycle` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=4db05a7973a9981025d8ffca834ae579ce9150382fd2d365c84a7db75d85eba6

```text
.ce/changelog/ce-476-claim-lifecycle.md
.ce/pr-manifests/ce-476-claim-lifecycle.md
.github/workflows/ce-claim-closeout.yml
docs/claims-lifecycle.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/claim_lifecycle.py
validators/tests/unit/test_ce_claim_closeout_workflow.py
validators/tests/unit/test_ce_claim_lifecycle_cli.py
validators/tests/unit/test_claim_lifecycle.py
```
