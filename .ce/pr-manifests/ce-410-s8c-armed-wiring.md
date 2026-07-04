# PR path manifest — creator-engine/ce-ops#410 · Conveyor armed-mode validation via sandbox runner

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-s8c-armed-wiring` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=8ea40da2bf59bd4916e116e7a067cfdc8bb5dee167d26fe0c8a133e88cf58c43

```text
.ce/changelog/ce-410-s8c-armed-wiring.md
.ce/pr-manifests/ce-410-s8c-armed-wiring.md
validators/creator_engine_validator/conveyor.py
validators/creator_engine_validator/conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon.py
```
