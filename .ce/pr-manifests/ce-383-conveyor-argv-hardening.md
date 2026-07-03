# PR path manifest — ce-ops#383 · Harden conveyor daemon argv ref handling

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-383-conveyor-argv-hardening` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=dae1ad5389dbb1e3d762cb9496ca0f0f39e2bd615e9ffe65a7b53eaf47b4e643

```text
.ce/changelog/ce-383-conveyor-argv-hardening.md
.ce/pr-manifests/ce-383-conveyor-argv-hardening.md
validators/creator_engine_validator/conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon.py
```
