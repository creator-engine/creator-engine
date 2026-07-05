# PR path manifest — ce-ops#453 · preflight skipped-test transparency

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-453-preflight-skip-transparency` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=8733b2c8a358f9ac74931726e42e69cc8ff364c9ffc1b947cb8509a32f73d978

```text
.ce/changelog/ce-453-preflight-skip-transparency.md
.ce/pr-manifests/ce-453-preflight-skip-transparency.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
```
