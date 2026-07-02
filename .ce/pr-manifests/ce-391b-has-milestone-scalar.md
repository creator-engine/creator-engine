# PR path manifest — ce-ops#391 · Fix forge triage milestone scalar classification

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-391b-has-milestone-scalar` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=47498771813b912731a4eb052d14e418a9ca2dcf86d093545fb6df5ac48a2673

```text
.ce/changelog/ce-391b-has-milestone-scalar.md
.ce/pr-manifests/ce-391b-has-milestone-scalar.md
validators/creator_engine_validator/forge_triage.py
validators/tests/unit/test_forge_triage.py
```
