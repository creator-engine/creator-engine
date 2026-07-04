# PR path manifest — ce-ops#388 · Conveyor harvest daemon shadow-mode launcher and entrypoint

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-388-conveyor-harvest-daemon` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=13e9d15905e719daec2e05db7416a3609ab5b8348512371de2980b4078c5b6ea

```text
.ce/changelog/ce-388-conveyor-harvest-daemon.md
.ce/pr-manifests/ce-388-conveyor-harvest-daemon.md
deploy/conveyor-daemon/ce-conveyor-daemon.service
deploy/conveyor-daemon/launch-conveyor-daemon.sh
deploy/daemons/run-daemon-container.sh
validators/creator_engine_validator/conveyor_daemon_runner.py
validators/tests/unit/test_conveyor_daemon_runner.py
```
