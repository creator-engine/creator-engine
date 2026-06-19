---
slug: ce120-wave3-reviewer-triage-wiring
date: 2026-06-19
kind: changed
scope: reviewer triage
issue: ce-ops#120
---

Extended reviewer-triage decision records with `triage_results`, a combined
per-candidate advisory routing view that joins eligibility and durable
availability into `selected`, `selectable`, `ineligible`, or `unavailable`
statuses.

The planner remains plan-only and non-authoritative: it still does not request
reviews, spawn reviewer venues, mint envelopes, approve, ratify, merge, or waive
policy.

Rebuilt the validator app wheel and refreshed the app-wheel checksum so the
offline packaging checks include `creator_engine_validator/reviewer_triage.py`.
