# PR path manifest — DGX JOB-1 receipt tree-identity blocker runbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref
dgx-job1-receipt-tree-identity-blocker-runbook` and requires this PR's
`base..HEAD` diff to equal exactly the authorized path-set below; this carrier
lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=3a90e90587a6e589ffdd2f300550c4d2f41557bde964e94142186dc4c616270a

```text
.ce/changelog/dgx-job1-receipt-tree-identity-blocker-runbook.md
.ce/pr-manifests/dgx-job1-receipt-tree-identity-blocker-runbook.md
docs/operations/WORKER_HOST_READINESS.md
```
