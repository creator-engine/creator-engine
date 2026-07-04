---
slug: ce-410-s8c-armed-wiring
date: 2026-07-04
kind: changed
scope: conveyor validation
issue: creator-engine/ce-ops#410
---

**Conveyor armed-mode validation via sandbox runner.**

- Wired armed conveyor validation through the validation sandbox runner and recorded receipts.
- Committed generated carriers before armed sandbox validation so receipts bind the prepared tree.
- Added an 8c interim fail-closed pre-push assertion: if the landed branch tip tree does not match the validation receipt tree, the item fails before push/PR open.
- Documented the 8c interim: slice 9 must promote `validation_ledger_binding` into the armed required-seam list.
- Design SSOT `/var/tmp/CE410_SLICE8_SPIKE_DESIGN_20260704.md` (sha256 `15db27aa632b1e9f67806665ce8e961e88913186446d14b638c164fb1e5d600f`) assigns full publish reverify to slice 10: re-derive `tree_sha` immediately before push/PR and confirm it equals the receipt-bound tree, with per-phase audit trail.
