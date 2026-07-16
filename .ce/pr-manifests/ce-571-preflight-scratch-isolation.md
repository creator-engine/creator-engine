# PR path manifest — ce-ops#571 · Isolate validate-pr scratch on disk-backed storage

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-571-preflight-scratch-isolation` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=cf8dd56e4f78191089c4541fecb70a8d1deddc1a9ca421938c7ed15a8037c020

```text
.ce/changelog/ce-571-preflight-scratch-isolation.md
.ce/pr-manifests/ce-571-preflight-scratch-isolation.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
```
