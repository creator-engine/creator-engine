# PR path manifest — ce-ops#388 · Fast-follow conveyor daemon lease UX and one-shot launcher flag

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-388-fastfollow-lease-ux` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=bf2f92bd19cfc070c7fa06d5e3f334bbe242bac20bae144c12d67af63f763f4f

```text
.ce/changelog/ce-388-fastfollow-lease-ux.md
.ce/pr-manifests/ce-388-fastfollow-lease-ux.md
deploy/conveyor-daemon/RUNBOOK.md
deploy/conveyor-daemon/launch-conveyor-daemon.sh
validators/creator_engine_validator/conveyor_daemon_runner.py
validators/tests/unit/test_conveyor_daemon_runner.py
```
