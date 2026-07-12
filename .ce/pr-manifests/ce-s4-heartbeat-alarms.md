# PR path manifest — none · feat(daemons): add heartbeat alarm consumer (S4)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-s4-heartbeat-alarms` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=c37d6454136a3995be699505f23ef19a7be0dfcbcda49293d9f714c69b548926

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-s4-heartbeat-alarms.md
.ce/pr-manifests/ce-s4-heartbeat-alarms.md
.ce/reference/cli.generated.md
deploy/systemd/ce-heartbeat-check.service
deploy/systemd/ce-heartbeat-check.timer
docs/reference/cli.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/daemon_heartbeat_alarm.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_daemon_heartbeat_alarm.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
