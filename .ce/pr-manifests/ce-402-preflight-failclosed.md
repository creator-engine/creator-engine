# PR path manifest — ce-ops#402 · Fail closed when baseline-diff pytest does not execute tests

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-402-preflight-failclosed` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=45b75d5656e3354ec8e39d12b730df0cff900a8751469b2c01533b358cc67125

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-402-preflight-failclosed.md
.ce/pr-manifests/ce-402-preflight-failclosed.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_pr_preflight.py
```
