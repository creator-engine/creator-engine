---
slug: ce-628-proof-tags
date: 2026-07-19
kind: docs
scope: operator-facing report verification discipline
issue: ce-ops#628
---

**Proof-tag discipline for Operator-facing claims.**

- Adds `docs/operations/PROOF_TAG_DISCIPLINE.md`: every factual claim in an
  Operator-facing report carries `[CONFIRMED]` (verified live this session),
  `[STATIC-VERIFIED]` (verified against code/config/artifact content, not
  live behavior), or `[OP-PROOF-REQ]` (vendor claim / unverified assertion
  needing Operator-visible proof before reliance).
- Untagged claims in decision-bearing reports default to `[OP-PROOF-REQ]`;
  tags apply at claim granularity, not paragraph; the tag names the
  verification performed, not the author's confidence.
- Adopted from the James-Hermes harness analysis; ratified 2026-07-19.
- Registers the new file in the `docs/operations` public-doc confidentiality
  exception ratchet so the internal-tree net-new-file guard passes.
