# PR path manifest — ce-ops#376 · Surface commissioned unscheduled issues in forge triage

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-376-unscheduled-sweep` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=385551f45fbb0822465c10eff871efc68258e6f134c9142d8e9c6a519c57f03f

- **Declared work class:** S

```text
.ce/changelog/ce-376-unscheduled-sweep.md
.ce/pr-manifests/ce-376-unscheduled-sweep.md
validators/creator_engine_validator/forge_triage.py
validators/tests/unit/test_forge_triage.py
```
