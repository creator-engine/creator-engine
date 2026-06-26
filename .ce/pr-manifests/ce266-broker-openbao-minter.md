# PR path manifest — ce-ops#266 · wire egress-broker minter to OpenBao App-key custody

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce266-broker-openbao-minter` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=ed88696e40907156039f8870c5bce2ae70d24ab42cd04097b82d49245032f86e

```text
.ce/changelog/ce266-broker-openbao-minter.md
.ce/pr-manifests/ce266-broker-openbao-minter.md
tools/egress-broker/apps.example.json
tools/egress-broker/egress_broker/config.py
tools/egress-broker/egress_broker/minter.py
validators/tests/unit/test_egress_vault_signer.py
```
