# PR path manifest — review-pickup OpenBao supplier gate

- **Declared work class:** S

This per-PR carrier lists the closed authorized path-set for this branch. The
branch is restricted to the Round 2 Unit A review-pickup OpenBao supplier work,
its deployment-binding documentation/test repair, and carrier files. Signed
artifacts, queue-daemon lease code, approval-wall behavior, and unrelated forge
code are out of scope.

Rebase reconciliation note: `origin/main` at
`6ce9527e1a9da3c578266db42b79625fe86392cd` already contains the required
review-pickup CLI flag/helper wiring in
`validators/creator_engine_validator/v3_cli.py` and the per-pass supplier retry
loop in `validators/creator_engine_validator/forge/review_pickup.py`. This
branch keeps those base implementations unchanged and only normalizes the
review-pickup OpenBao default path constant plus this carrier.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=2a97b712f2406a86cc7a9dbe7642cd42217e7a9a9e2a99d1a1332191b6696737

```text
.ce/changelog/ce239-wall-openbao-supplier.md
.ce/pr-manifests/ce239-wall-openbao-supplier.md
deploy/systemd/README.md
deploy/systemd/install-gate-daemons-systemd.sh
validators/creator_engine_validator/secret_identity.py
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_review_pickup_openbao_supplier.py
validators/tests/unit/test_v3_cli.py
```
