# PR path manifest — ce-ops#235 · gate dequeue + settle

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce235-gate-dequeue-settle` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=9014af579f501fdd23c1ef5df8d133bca9d6e5434a2f3ab5c1b1b3b9a7cb1ba4

```text
.ce/changelog/ce235-gate-dequeue-settle.md
.ce/pr-manifests/ce235-gate-dequeue-settle.md
deploy/systemd/README.md
deploy/systemd/ce-integrator-daemon.service
deploy/systemd/install-gate-daemons-systemd.sh
docs/operations/INTEGRATOR_BELT_DAEMON.md
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_integrator_belt.py
```
