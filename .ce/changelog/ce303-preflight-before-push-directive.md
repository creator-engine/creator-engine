---
slug: ce303-preflight-before-push-directive
date: 2026-06-27
kind: docs
scope: controller playbooks / author docs
issue: ce-ops#303
---

**propagate full-preflight-before-push standing directive to dev fleet.**

- **Declared work class:** tiny

- Propagates the standing Operator directive to the durable in-repo SSOT
  surfaces so it reaches every seat on relaunch and in every dispatch brief:
  run the FULL local validator preflight (`ce validate-pr`, CI-parity)
  before every self-push or commit-for-harvest; do not discover gates via CI.
- Fast iteration once ce-ops#11 (test-tier split) lands on main:
  `pytest -m "not slow"` — iteration only; the full suite still gates push.
- Surfaces: `docs/operations/AUTHOR_A_CE_VALID_PR.md` (seat-facing author
  playbook) and `playbooks/controller/briefs/dispatch.md` (per-dispatch brief).
