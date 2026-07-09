# PR path manifest - ce-504-broker-arming-blockers

This per-PR carrier lists the closed authorized path-set for this branch. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-504-broker-arming-blockers` and requires this branch's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=c8200edee802eebb7845a466b38dbed375ece5e277f6b1e246b6abddf53b9a61

```text
.ce/changelog/ce-504-broker-arming-blockers.md
.ce/pr-manifests/ce-504-broker-arming-blockers.md
tools/host-ops-broker/host_ops_broker/audit.py
tools/host-ops-broker/host_ops_broker/broker.py
tools/host-ops-broker/host_ops_broker/config.py
validators/tests/unit/test_host_ops_broker_audit.py
validators/tests/unit/test_host_ops_broker_config.py
```
