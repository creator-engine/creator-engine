# PR path manifest — ce-daemon-heartbeat-contract-s1

This carrier lists the closed five-path Slice 1 daemon-heartbeat contract.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

COMPARISON_BASE_SHA=82374144edebd4ad20eeeb78e7a6103383d93ad4

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=b6c5a686e3750393d4624d6ba97d4646a07d6ccae6e0b93db711dc2ab95e70cd

```text
.ce/changelog/ce-daemon-heartbeat-contract-s1.md
.ce/pr-manifests/ce-daemon-heartbeat-contract-s1.md
validators/creator_engine_validator/daemon_heartbeat.py
validators/creator_engine_validator/schemas/daemon-heartbeat.schema.yaml
validators/tests/unit/test_daemon_heartbeat.py
```
