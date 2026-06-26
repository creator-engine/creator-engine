---
slug: ce265-egress-broker-vps-deploy
date: 2026-06-26
kind: feat
scope: deploy
issue: ce-ops#265
---

**deploy egress self-push broker for VPS canary seat.**

Wire the egress self-push broker (built in #469) into the VPS launcher (`run-vps-runsc.sh`) by adding the optional `CE_VPS_EGRESS_BROKER_SOCKET` socket bind-mount, mirroring the existing DGX pattern. Add `deploy/systemd/ce-egress-broker.service` so the host broker can be supervised by systemd on the VPS. Extend unit tests to assert broker-mount and systemd-unit correctness.
