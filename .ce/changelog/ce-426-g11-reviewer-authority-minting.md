---
slug: ce-426-g11-reviewer-authority-minting
date: 2026-07-06
kind: changed
scope: lane launcher reviewer authority
issue: ce-ops#426
---

**In-launcher reviewer-authority envelope minting.**

- Adds `ce lane launch --mint-reviewer-authority` for distinct reviewer venues, producing a lane-scoped reviewer-authority envelope under ignored ledger state.
- Reuses the existing schema validation and `CE_REVIEWER_AUTHORITY_REF` hook carrier so minted and pre-existing envelopes share the same fail-closed path.
