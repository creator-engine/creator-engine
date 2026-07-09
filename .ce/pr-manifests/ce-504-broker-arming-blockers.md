# PR path manifest - ce-504-broker-arming-blockers

This per-PR carrier lists the closed authorized path-set for this branch. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-504-broker-arming-blockers` and requires this branch's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=d740bf20ade2d13cf69aec144b0e0755add2590431f08ee6330e0e56047f2031

```text
.ce/changelog/ce-504-broker-arming-blockers.md
.ce/pr-manifests/ce-504-broker-arming-blockers.md
.ce/wt-504/READY
tools/host-ops-broker/host_ops_broker/audit.py
tools/host-ops-broker/host_ops_broker/broker.py
tools/host-ops-broker/host_ops_broker/config.py
validators/tests/unit/test_host_ops_broker_audit.py
validators/tests/unit/test_host_ops_broker_config.py
```
