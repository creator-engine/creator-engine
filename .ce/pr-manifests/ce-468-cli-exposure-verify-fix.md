# PR path manifest — ce-ops#468 · fix: verify_cli predicate tolerates onboard->install verb rename

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-468-cli-exposure-verify-fix` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=85ad7efe29e6395c0a42866b1ebd9cf9671ec38524b1fedb6878878e08e271c5

```text
.ce/changelog/ce-468-cli-exposure-verify-fix.md
.ce/pr-manifests/ce-468-cli-exposure-verify-fix.md
validators/creator_engine_validator/onboard_apply.py
validators/tests/unit/test_onboard_apply.py
```
