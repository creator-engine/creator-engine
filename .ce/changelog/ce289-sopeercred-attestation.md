---
slug: ce289-sopeercred-attestation
date: 2026-06-27
kind: added
scope: egress-broker / host socket attestation
issue: ce-ops#289
work_class: story
---

**feat(ce-ops#289): audit SO_PEERCRED for egress self-push broker connections**

- `tools/egress-broker/egress_broker/host_broker.py`: read Linux
  `SO_PEERCRED` on each accepted self-push Unix-socket connection and append a
  `self_push_peercred` JSONL audit record before request handling.
- Default behavior is RECORD+FLAG only when no expected UID/GID profile is
  configured, preserving existing self-push behavior; making hard-reject the
  default remains a follow-on.
- Hosts can configure expected peer UID/GID profiles and optionally reject
  mismatches with `peer_credential_unexpected`.
- `validators/tests/unit/test_egress_host_broker.py`: add focused AF_UNIX
  coverage for real peer credentials, matching allow, opt-in reject, and
  default flag-and-proceed behavior.
