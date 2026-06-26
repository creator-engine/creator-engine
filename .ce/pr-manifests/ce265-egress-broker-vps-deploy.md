# PR path manifest — ce-ops#265 · deploy egress self-push broker for VPS canary seat

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce265-egress-broker-vps-deploy` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=ecd98544d665cbd0d51ceae742ea306ebf59a568bac0de6871e2e55b817600ab

```text
.ce/changelog/ce265-egress-broker-vps-deploy.md
.ce/pr-manifests/ce265-egress-broker-vps-deploy.md
deploy/systemd/ce-egress-broker.service
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_vps_runsc_launcher.py
```
