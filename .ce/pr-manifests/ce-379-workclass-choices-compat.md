# PR path manifest — ce-379 · Work-class validator choices accept canonical and legacy names

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-379-workclass-choices-compat` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=fe80208dd57585eea26c3d16b2b3db779c2a9bc543a063cac8c6e6ac53dc2734

```text
.ce/changelog/ce-379-workclass-choices-compat.md
.ce/pr-manifests/ce-379-workclass-choices-compat.md
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_ce_validate_pr_cli.py
validators/tests/unit/test_pr_preflight.py
```
