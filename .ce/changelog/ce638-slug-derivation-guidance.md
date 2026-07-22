---
slug: ce638-slug-derivation-guidance
date: 2026-07-22
kind: changed
scope: governed PR authoring guidance
issue: ce-ops#638
---

Reframe carrier-slug guidance around the durable rule: invoke
`branch_slug(head_ref)` or `write_carriers`; never predict a carrier slug by
hand. The existing Manifest-fidelity recipe remains the concrete programmatic
path.
