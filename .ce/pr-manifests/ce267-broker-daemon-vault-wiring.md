# PR path manifest — ce-ops#267 · wire egress-broker daemon to vault signer + AppRole login

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce267-broker-daemon-vault-wiring` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=da2081fac0b80c098541f2f764a1b7ddb67c4965223d73359e85d9ff82e4e234

```text
.ce/changelog/ce267-broker-daemon-vault-wiring.md
.ce/pr-manifests/ce267-broker-daemon-vault-wiring.md
deploy/systemd/install-gate-daemons-systemd.sh
tools/egress-broker/ce_egress_self_push_broker.py
validators/tests/unit/test_egress_broker_daemon_vault.py
```
