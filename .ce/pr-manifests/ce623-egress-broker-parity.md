# PR path manifest — ce-ops#623 · dev-4 egress broker parity

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce623-egress-broker-parity` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=e72959f8365b6b4b8ed6a94b3337701cd0bc139256e098e9f720310c215c3c22

```text
.ce/changelog/ce623-egress-broker-parity.md
.ce/pr-manifests/ce623-egress-broker-parity.md
deploy/egress-broker/README.md
deploy/egress-broker/dev-3/ce-egress-broker.env
deploy/egress-broker/dev-4/broker-dev4.json
deploy/egress-broker/dev-4/ce-egress-broker.env
deploy/egress-broker/fleet-seats.json
deploy/egress-broker/v1/preflight-peer-identity.sh
deploy/systemd/ce-egress-broker-dev-4-liveness.service
deploy/systemd/ce-egress-broker-dev-4-liveness.timer
deploy/systemd/ce-egress-broker-dev-4.service
deploy/systemd/ce-egress-broker-dev-4.socket
deploy/systemd/ce-egress-broker-liveness.service
deploy/systemd/ce-egress-broker-liveness.timer
deploy/systemd/ce-egress-broker.service
validators/tests/unit/test_egress_broker_fleet_parity.py
validators/tests/unit/test_egress_broker_peer_identity_preflight.py
```
