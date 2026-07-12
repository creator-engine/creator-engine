# PR path manifest — none · feat(daemons): belt and integrator heartbeat adoption (S2)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-daemon-heartbeat-belt-integrator-s2` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=790601bd2ce6e5547473226170bfbafc159de13512cda36b8e815d2e0c4b1d80

```text
.ce/changelog/ce-daemon-heartbeat-belt-integrator-s2.md
.ce/pr-manifests/ce-daemon-heartbeat-belt-integrator-s2.md
deploy/systemd/ce-belt-daemon.service
deploy/systemd/ce-integrator-daemon.service
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_integrator_belt.py
validators/tests/unit/test_pickup.py
validators/tests/unit/test_review_pickup.py
```
