# PR path manifest — ce-ops#302 · Broker namespace allowlist

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-302-broker-namespace` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** tiny

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=8ed72053e76c56cc913721fa90fa30c939d742a33c2197a517cde34de744e2ed

```text
.ce/changelog/ce-302-broker-namespace.md
.ce/pr-manifests/ce-302-broker-namespace.md
tools/egress-broker/apps.example.json
tools/egress-broker/ce_egress_self_push_broker.py
tools/egress-broker/egress_broker/policy.py
validators/tests/unit/test_egress_policy.py
```
