---
slug: ce171-protection-floor-unenforceable
date: 2026-06-21
kind: fixed
scope: install / onboard protection-floor diagnostics
issue: ce-ops#171
base: 297be9f08f71f5f454594b6519dc20d6ab61ed84
---

Make `cev3 onboard --plan` and `cev3 onboard --apply` fail closed when GitHub
reports that the target repository cannot enforce the CE protection floor.

- Added a shared classifier for GitHub plan/capability 403s such as "Upgrade to
  GitHub Pro or make this repository public" across branch protection and
  repository Rulesets.
- Surfaced `protection_floor_unenforceable` with remediation to upgrade to
  GitHub Team/Pro or make the repository public.
- Preserved the Ruleset fallback when classic branch protection is unavailable
  but repository Rulesets can still verify the CE floor.
- Added offline tests for planner, CLI preflight, apply-leg, live-driver, and
  adoption preserved-check diagnostics.
