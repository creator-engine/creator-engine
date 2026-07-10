# PR path manifest - ce-f2-gate-hardening - Gate hardening: homeless attempt log, disk-headroom refusal, liveness state export

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-f2-gate-hardening` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=28b5dde45ff1e7e0ccea55d2b306851dea35467a1976e01ff794428a1cc7dd80

```text
.ce/changelog/ce-f2-gate-hardening.md
.ce/pr-manifests/ce-f2-gate-hardening.md
deploy/daemons/run-daemon-container.sh
deploy/queue-daemon/ce-queue-daemon.service
deploy/queue-daemon/launch-queue-daemon.sh
validators/creator_engine_validator/forge/integrator_belt.py
validators/tests/unit/test_f2_gate_hardening.py
```
