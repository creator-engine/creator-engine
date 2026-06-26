# PR path manifest — ce-ops#268 · wire self-review broker daemon to vault signer + AppRole login

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce268-self-review-daemon-vault-wiring` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=31f3730586f6570a322e61624d4964bc3fae3433d7ed6eab1627324a85f4f760

```text
.ce/changelog/ce268-self-review-daemon-vault-wiring.md
.ce/pr-manifests/ce268-self-review-daemon-vault-wiring.md
deploy/systemd/ce-egress-self-review.service
deploy/systemd/install-gate-daemons-systemd.sh
tools/egress-broker/ce_egress_self_review_broker.py
validators/tests/unit/test_egress_review_daemon_vault.py
```
