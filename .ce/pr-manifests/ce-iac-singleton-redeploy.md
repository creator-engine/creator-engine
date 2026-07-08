# PR path manifest — Operator decision 1 · Add singleton daemon redeploy surface

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-iac-singleton-redeploy` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=a5f6f5064c3f64fc8acfa3ae533c89e5f6a76b9a559af1b75fba47ebfd50e57e

```text
.ce/changelog/ce-iac-singleton-redeploy.md
.ce/pr-manifests/ce-iac-singleton-redeploy.md
deploy/singleton-redeploy/redeploy-singleton.sh
deploy/singleton-redeploy/smoke-singleton-redeploy.sh
docs/operations/SINGLETON_DAEMON_REDEPLOY_RUNBOOK.md
validators/creator_engine_validator/public_docs_confidentiality.py
```
