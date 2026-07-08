# PR path manifest — Operator decision 1 · Add singleton daemon redeploy surface

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-iac-singleton-redeploy` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=5c5fb1342b68f2e54df4359642db5f8a78de2beb9ff7ee60ceaf3cb73f1f3b33

```text
.ce/changelog/ce-iac-singleton-redeploy.md
.ce/pr-manifests/ce-iac-singleton-redeploy.md
deploy/singleton-redeploy/redeploy-singleton.sh
deploy/singleton-redeploy/smoke-singleton-redeploy.sh
docs/operations/SINGLETON_DAEMON_REDEPLOY_RUNBOOK.md
```
