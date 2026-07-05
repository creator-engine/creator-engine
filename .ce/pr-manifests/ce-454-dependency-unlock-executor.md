# PR path manifest — creator-engine/ce-ops#454 · Merge-triggered dependency-unlock executor, SHADOW-first (slice 1)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-454-dependency-unlock-executor` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=ecce09f9704b9d13b24c5f27c8f2b36f04eaab4e61ace3672b76706ab7ffb3eb

```text
.ce/changelog/ce-454-dependency-unlock-executor.md
.ce/pr-manifests/ce-454-dependency-unlock-executor.md
.github/workflows/ce-dependency-unlock.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/dependency_unlock.py
validators/tests/unit/test_dependency_unlock.py
```
