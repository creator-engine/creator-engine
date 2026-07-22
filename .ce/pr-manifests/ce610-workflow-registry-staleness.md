# PR path manifest — ce-ops#610 · Fail closed on stale workflow permission profiles

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce610-workflow-registry-staleness` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=84253ed24513335f80828e07c87f9d5526acd7d13655796afcfbd8a9d1456e57

```text
.ce/changelog/ce610-workflow-registry-staleness.md
.ce/pr-manifests/ce610-workflow-registry-staleness.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
```
