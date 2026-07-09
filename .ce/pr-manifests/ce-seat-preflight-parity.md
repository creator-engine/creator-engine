# PR path manifest - ce-seat-preflight-parity

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-seat-preflight-parity` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=2d58821f4694695023004848c1a05c35004a94799a08e8a7ee8c21ddff94b1c4

```text
.ce/changelog/ce-seat-preflight-parity.md
.ce/pr-manifests/ce-seat-preflight-parity.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
```
