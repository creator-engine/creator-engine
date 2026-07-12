# PR path manifest — none · feat(daemons): add heartbeat alarm consumer (S4)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-s4-heartbeat-alarms` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=117bd71b170a3030b43dbbbbda6818b0071b17ea014312c1ffa1576caf99f14d

```text
.ce/changelog/ce-s4-heartbeat-alarms.md
.ce/pr-manifests/ce-s4-heartbeat-alarms.md
deploy/systemd/ce-heartbeat-check.service
deploy/systemd/ce-heartbeat-check.timer
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/daemon_heartbeat_alarm.py
validators/tests/unit/test_daemon_heartbeat_alarm.py
```
