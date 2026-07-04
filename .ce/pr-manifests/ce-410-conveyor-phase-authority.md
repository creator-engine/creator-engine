# PR path manifest — ce-ops#410 · Type conveyor git runner phases and pass explicit subprocess envs

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-conveyor-phase-authority` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=feac6a9624d2d435b13ba34e6c9fa78a38b44555dd069a2122804c8f73d3dfb5

```text
.ce/changelog/ce-410-conveyor-phase-authority.md
.ce/pr-manifests/ce-410-conveyor-phase-authority.md
validators/creator_engine_validator/conveyor.py
validators/creator_engine_validator/conveyor_daemon.py
validators/tests/unit/test_conveyor.py
validators/tests/unit/test_conveyor_daemon.py
```
