# PR path manifest — ce-491-ledger-append-serialization

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-491-ledger-append-serialization` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=41003f040a1a104fb33fe5c6387cfc53c20d204c66b8afa81dfda4fb0e4983f3

```text
.ce/changelog/ce-491-ledger-append-serialization.md
.ce/pr-manifests/ce-491-ledger-append-serialization.md
docs/design/ce-491-ledger-append-serialization-slice1.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_pr_preflight.py
```
