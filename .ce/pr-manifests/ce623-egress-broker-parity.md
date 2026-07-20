# PR path manifest — ce-ops#623 · dev-4 egress broker parity

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce623-egress-broker-parity-dev3-leaf` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=b71f9ac7330d1550c7f50fba20c335d0972bceae514008e2c49b04c4c507af38

```text
.ce/changelog/ce623-egress-broker-parity.md
.ce/pr-manifests/ce623-egress-broker-parity.md
deploy/egress-broker/dev-4/broker-dev4.json
deploy/egress-broker/dev-4/ce-egress-broker.env
deploy/egress-broker/fleet-seats.json
deploy/systemd/ce-egress-broker-dev-4-liveness.service
deploy/systemd/ce-egress-broker-dev-4-liveness.timer
deploy/systemd/ce-egress-broker-dev-4.service
deploy/systemd/ce-egress-broker-dev-4.socket
validators/tests/unit/test_egress_broker_fleet_parity.py
```
