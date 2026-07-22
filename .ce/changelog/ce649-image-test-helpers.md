---
slug: ce649-image-test-helpers
date: 2026-07-22
kind: fixed
scope: static image-contract test support
issue: ce-ops#649
---

**Share image-contract token helpers.**

Factor the four duplicated Dockerfile RUN token helpers into one shared test-support module, with quote/substitution-aware command splitting.

Add nested-substitution and naked-package negative coverage so image contracts continue to reject non-executing mentions.
