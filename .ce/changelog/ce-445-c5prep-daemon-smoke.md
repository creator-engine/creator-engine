---
slug: ce-445-c5prep-daemon-smoke
date: 2026-07-05
kind: changed
scope: deploy/daemons
issue: ce-ops#445
work_class: story
---

**Add daemon container stateful restart smoke coverage.**

- Added a host-operator smoke script that runs the canonical daemon container
  adapter twice against one scratch state root and asserts lease release,
  reacquisition, Docker uid ownership, and (via a full recursive content scan
  of the scratch state root, not just known mount points) absence of the
  smoke's signing-secret content on host state after stop, with best-effort
  container/runner cleanup on any exit path.
- Documented the daemon image uid ownership contract and first-boot Docker
  remediation in the daemon container README.
- Aligned canonical image Dockerfile runtime dependency check order and added
  static/unit coverage for the smoke contract and Docker missing-root branch.
