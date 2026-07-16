---
slug: ce-566-governed-codex-worker-launcher
date: 2026-07-16
kind: feature
scope: governed Codex one-shot worker launcher
issue: ce-ops#566, ce-ops#567
---

**Add the policy-bound `ce worker launch` one-shot planner.**

- Adds a strict tracked policy and pure-plan-first external Codex launcher with
  deterministic argv, run-id/output, policy-owned binary/sandbox/model/effort,
  canonical add-dir selection, and hermetic injected-runner coverage.
- Documents the no-ambient-PATH/no-host-config and pre-run refusal boundary.
- Corrects the VPS launcher to use the stable governed x86_64 image tag by
  default and keeps exact `CE_VPS_CONTAINER_NAME` targeting for removal,
  readiness, and diagnostics without image-ancestor selectors.
