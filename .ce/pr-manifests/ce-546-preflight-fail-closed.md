# PR path manifest - ce-546 preflight fail-closed

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-546-preflight-fail-closed` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e70175f6d4271dd81c7459f0a0c66dcaa74518c776c8128b611510b7d1988995

```text
.ce/changelog/ce-546-preflight-fail-closed.md
.ce/pr-manifests/ce-546-preflight-fail-closed.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
```
