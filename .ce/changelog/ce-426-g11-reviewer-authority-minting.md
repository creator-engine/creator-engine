---
slug: ce-426-g11-reviewer-authority-minting
date: 2026-07-06
kind: changed
scope: lane launcher reviewer authority
issue: ce-ops#426
---

**G11 reviewer-authority in-launcher minting.**

- Adds `ce lane launch --mint-reviewer-authority` for distinct reviewer venues, producing a lane-scoped reviewer-authority envelope under ignored ledger state.
- Reuses the existing schema validation and `CE_REVIEWER_AUTHORITY_REF` hook carrier so minted and pre-existing envelopes share the same fail-closed path.
- Binds launcher-minted envelopes to `capability: independent_review_venue`, short expiry, single-use venue-launch consumption, and actor-vs-target-author self-review refusal.
- Delays writing minted envelopes until all pre-spawn refusal gates pass, so a refused venue launch cannot leave a valid unconsumed reviewer-authority artifact behind.
- Ensures approval-capable broker/proxy paths reject review-venue-only capability envelopes instead of treating them as approval authority.
- Keeps hook-side reviewer-venue envelopes scoped away from approval-capable `gh pr review --approve`; approval still requires a distinct authority path.
