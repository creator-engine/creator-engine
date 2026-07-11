---
slug: ce-539-checkpoint-skill
date: 2026-07-11
kind: added
scope: controller continuity checkpoint skill
issue: ce-ops#539
---

**Add a redaction-safe controller checkpoint skill.**

- Requires an untracked, SHA-256-verified resume-state file containing only
  delta since the prior checkpoint.
- Separates probed, asserted, and unknown facts while preserving authority and
  role boundaries.
- Provides deterministic completeness and safe resume procedures without
  creating readiness, forge, or gate side effects.
