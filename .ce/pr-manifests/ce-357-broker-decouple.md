# PR path manifest — ce-ops#357 · Decouple self-review broker from seat working trees

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-357-broker-decouple` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=2dfb4b0bdc34da8ce031ba39210179ffcaf420702e1c1f86823339105678ac77

```text
.ce/changelog/ce-357-broker-decouple.md
.ce/pr-manifests/ce-357-broker-decouple.md
deploy/systemd/ce-egress-self-review.service
deploy/systemd/install-gate-daemons-systemd.sh
tools/egress-broker/ce_egress_self_review_broker.py
tools/egress-broker/update-stable-broker-checkout.sh
validators/tests/unit/test_egress_self_review_broker.py
validators/tests/unit/test_egress_stable_broker_checkout.py
validators/tests/unit/test_gate_daemons_systemd.py
```
