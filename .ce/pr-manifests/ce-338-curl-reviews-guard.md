# PR path manifest — ce-ops#338 · block curl raw PR review approvals

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-338-curl-reviews-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=03f5b406af04f78d0fae0ea5c216691fdcfa318efcd632158b32a0c7aebccb1a

```text
.ce/changelog/ce-338-curl-reviews-guard.md
.ce/pr-manifests/ce-338-curl-reviews-guard.md
validators/creator_engine_validator/hook_check.py
validators/tests/unit/test_hook_check_reviewer_authority.py
```
