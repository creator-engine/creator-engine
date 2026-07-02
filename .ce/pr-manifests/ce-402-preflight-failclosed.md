# PR path manifest — ce-ops#402 · Fail closed when baseline-diff pytest does not execute tests

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-402-preflight-failclosed` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=d54d6fd8dfab1e0523105b38f383f0d43c4ba90a1de75539b38322c7d8b96bf7

```text
.ce/changelog/ce-402-preflight-failclosed.md
.ce/pr-manifests/ce-402-preflight-failclosed.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
```
