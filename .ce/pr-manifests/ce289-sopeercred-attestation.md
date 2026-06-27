---
slug: ce289-sopeercred-attestation
date: 2026-06-27
kind: pr-manifest
scope: egress-broker
issue: ce-ops#289
work_class: story
---

# PR path manifest - ce-ops#289 - SO_PEERCRED self-push broker attestation

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce289-sopeercred-attestation` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

- **Declared work class:** story

Scope: ce-ops#289 adds host-side SO_PEERCRED peer-credential attestation for the
egress self-push Unix-socket broker. The default is RECORD+FLAG for
compatibility; opt-in reject is available for unexpected peers, and
hard-reject-by-default remains follow-on work.

Per-file purpose:
- **`.ce/changelog/ce289-sopeercred-attestation.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce289-sopeercred-attestation.md`** *(A)* - this carrier.
- **`tools/egress-broker/egress_broker/host_broker.py`** *(M)* - peercred read,
  audit record, and optional reject gate.
- **`validators/tests/unit/test_egress_host_broker.py`** *(M)* - socket-level
  unit coverage for audit, allow, reject, and flag decisions.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=b38effcc46b9dbc0394f78600c2e45d973c5cbdb8a72a806ab714feedcdc759a

```text
.ce/changelog/ce289-sopeercred-attestation.md
.ce/pr-manifests/ce289-sopeercred-attestation.md
tools/egress-broker/egress_broker/host_broker.py
validators/tests/unit/test_egress_host_broker.py
```
