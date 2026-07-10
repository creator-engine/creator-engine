# PR path manifest — review-pickup OpenBao supplier gate

- **Declared work class:** S

This per-PR carrier lists the closed authorized path-set for this branch. The
branch is restricted to the Round 2 Unit A review-pickup OpenBao supplier work
and its carrier files. Deployment files, signed artifacts, queue-daemon lease
code, approval-wall behavior, and unrelated forge code are out of scope.

Rebase reconciliation note: `origin/main` at
`6ce9527e1a9da3c578266db42b79625fe86392cd` already contains the required
review-pickup CLI flag/helper wiring in
`validators/creator_engine_validator/v3_cli.py` and the per-pass supplier retry
loop in `validators/creator_engine_validator/forge/review_pickup.py`. This
branch keeps those base implementations unchanged and only normalizes the
review-pickup OpenBao default path constant plus this carrier.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=4536a3a1a4cd10ffec78b4f59d7fd74b703057416024bc609f02950cac55e5b1

```text
.ce/changelog/ce239-wall-openbao-supplier.md
.ce/pr-manifests/ce239-wall-openbao-supplier.md
validators/creator_engine_validator/secret_identity.py
```
