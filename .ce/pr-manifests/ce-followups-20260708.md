# PR path manifest — ce-ops#504 · Review follow-up batch for merged PR minors

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-followups-20260708` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=f2789fa5443b5af6d34928533ac771f68d665a24747e9a5758186a872d9e934d

```text
.ce/changelog/ce-followups-20260708.md
.ce/pr-manifests/ce-followups-20260708.md
tools/host-ops-broker/host_ops_broker/audit.py
tools/host-ops-broker/host_ops_broker/broker.py
tools/host-ops-broker/host_ops_broker/kill_switch.py
tools/host-ops-broker/host_ops_broker/verb_schema.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_host_ops_broker_audit.py
validators/tests/unit/test_host_ops_broker_kill_switch.py
validators/tests/unit/test_host_ops_broker_verb_schema.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_wheel_bake.py
```
