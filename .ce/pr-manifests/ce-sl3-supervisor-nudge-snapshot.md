# PR path manifest — SL-3 supervisor nudge snapshot

This per-PR carrier lists the closed authorized path-set for this slice.
Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=5782bafc8517cbb851ed6cb138d5640ac84e42a5ce48b538f43409b6cca95b1e

```text
.ce/changelog/ce-sl3-supervisor-nudge-snapshot.md
.ce/pr-manifests/ce-sl3-supervisor-nudge-snapshot.md
validators/creator_engine_validator/forge/supervisor_nudge_snapshot.py
validators/tests/unit/test_supervisor_nudge_snapshot.py
```
