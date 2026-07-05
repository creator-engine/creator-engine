---
slug: ce-388-d2-pickup-openbao-deploy-tests
date: 2026-07-05
kind: story
scope: review-pickup OpenBao deployment surface
work_class: story
---

**Add the review-pickup OpenBao deployment surface and D1 behavior coverage.**

- Gate daemon systemd docs now describe the OpenBao env variables, exact
  allowed SecretRef entry, and static-token fallback during rollout.
- The review-pickup systemd unit carries a commented OpenBao-ready replacement
  command while the active command preserves the static fallback.
- Unit tests cover review-pickup token supplier construction, fork-unsafe
  `env:` target rejection, per-pass token refresh, retry logging, and bounded
  supervisor restart behavior.
