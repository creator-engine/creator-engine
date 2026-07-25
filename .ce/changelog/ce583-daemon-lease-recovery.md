---
slug: ce583-daemon-lease-recovery
date: 2026-07-25
kind: fixed
scope: queue daemon lease recovery
issue: ce-ops#583
---

**Fail closed for the queue-daemon locked recovery deletion race.**

- Normalize a post-eligibility lease deletion into the existing singleton lease
  refusal path and exit 73 without starting a child or taking over the lease.
- Cover unexpected lease payload fields with no audit record or replacement.
- Record the intentionally private, launcher-coupled daemon lease recovery seam
  at its definition site.
