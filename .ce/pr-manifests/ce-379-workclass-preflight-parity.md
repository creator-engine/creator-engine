# PR path manifest - ce-379 work-class preflight parity

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-379-workclass-preflight-parity` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=326968003a0904afa6c432ccd4fc9ded071d2b1ccacc236a843e9dff88537475

```text
.ce/changelog/ce-379-workclass-preflight-parity.md
.ce/pr-manifests/ce-379-workclass-preflight-parity.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_work_sizing_floor.py
```
