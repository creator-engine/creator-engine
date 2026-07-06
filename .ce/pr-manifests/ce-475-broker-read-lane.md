# PR path manifest — ce-ops#475 · Broker read lane

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set
for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests
--head-ref ce-475-broker-read-lane` and requires this PR's `base..HEAD` diff to equal exactly
the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=9e62e22b010296b6a0646dce45c79523b896da0966c6c1d0096d1777c6e02228

```text
.ce/changelog/ce-475-broker-read-lane.md
.ce/pr-manifests/ce-475-broker-read-lane.md
tools/egress-broker/README.md
tools/egress-broker/ce_egress_forge_read_broker.py
tools/egress-broker/egress_broker/audit.py
tools/egress-broker/egress_broker/forge_read.py
validators/tests/unit/test_egress_forge_read_broker.py
```
