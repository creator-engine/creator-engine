# PR path manifest — ce-fix-artifacts-hint · Fix completion-report artifacts inspect hints

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-fix-artifacts-hint` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=86a93dcdd051654df13b894460d65621fa4daa71b9b83b46e7a99a7d6f719824

```text
.ce/changelog/ce-fix-artifacts-hint.md
.ce/pr-manifests/ce-fix-artifacts-hint.md
validators/creator_engine_validator/v3_report.py
validators/tests/unit/test_v3_report.py
```

- **Declared work class:** tiny
