# PR path manifest — ce-ops#636 · brain correction statement preservation

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce636-brain-correct-statement-preservation` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=d90213128a1e86fd146de9485156e946527af9e2df49086db1fdb3ed64bfbba1

```text
.ce/changelog/ce636-brain-correct-statement-preservation.md
.ce/pr-manifests/ce636-brain-correct-statement-preservation.md
.ce/reference/cli.generated.md
validators/creator_engine_validator/brain_runtime.py
validators/creator_engine_validator/ce_cli.py
validators/tests/integration/test_ce_brain_cli.py
```
