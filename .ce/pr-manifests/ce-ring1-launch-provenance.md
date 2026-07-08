# PR path manifest — ce-ops#480 · Codex Ring 1 launch provenance

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-ring1-launch-provenance` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=3f94e974bd9757ba660d1c385054620081e2b78694d2b89ca083c70b1857f806

```text
.ce/changelog/ce-ring1-launch-provenance.md
.ce/pr-manifests/ce-ring1-launch-provenance.md
docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md
validators/creator_engine_validator/harness_matrix.py
validators/tests/unit/test_harness_matrix.py
```
