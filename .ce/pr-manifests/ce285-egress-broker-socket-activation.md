---
slug: ce285-egress-broker-socket-activation
date: 2026-06-27
issue: ce-ops#285
work_class: story
---

# PR path manifest - ce-ops#285 - egress broker socket activation

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce285-egress-broker-socket-activation`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=1e6853e1cdeb21049b1fa31a59b7d7af4a51e5ab7f28b65a6b6388a3487b8bdd

```text
.ce/changelog/ce285-egress-broker-socket-activation.md
.ce/pr-manifests/ce285-egress-broker-socket-activation.md
deploy/systemd/ce-egress-broker.service
deploy/systemd/ce-egress-broker.socket
deploy/systemd/ce-egress-self-review.service
deploy/systemd/ce-egress-self-review.socket
deploy/systemd/install-gate-daemons-systemd.sh
tools/egress-broker/ce_egress_self_push_broker.py
tools/egress-broker/ce_egress_self_review_broker.py
tools/egress-broker/egress_broker/__init__.py
tools/egress-broker/egress_broker/host_broker.py
validators/tests/unit/test_egress_host_broker.py
validators/tests/unit/test_egress_self_review_broker.py
validators/tests/unit/test_gate_daemons_systemd.py
```
