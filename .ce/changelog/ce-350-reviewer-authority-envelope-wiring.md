---
slug: ce-350-reviewer-authority-envelope-wiring
date: 2026-06-28
kind: changed
scope: authority spine
issue: ce-ops#350
---

**Reviewer authority envelope wiring.**

- Loads CE_REVIEWER_AUTHORITY_REF as a validated broker APPROVE fallback when no inline envelope is supplied.
- Keeps inline envelope authority precedence and COMMENT behavior unchanged.
- Adds live hook and broker fail-closed coverage for reviewer-authority carrier behavior.
