---
slug: ce-509-release-acceptance-design
ticket: CE-509
type: design
scope: release acceptance stage
---

Designs the release-acceptance stage between merge and ship.

- Defines the RC-to-promote state machine and repository-visible acceptance
  record location.
- Makes the existing fresh-tenant rehearsal harness the default promotion
  evidence path.
- Requires release-ticket closure to link acceptance evidence, including
  persistent-state probes for deploy-class claims.
- Names the ring-0 dogfood seat as the first consumer after promotion.
