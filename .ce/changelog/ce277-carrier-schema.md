---
slug: ce277-carrier-schema
date: 2026-06-27
kind: feature
scope: surface-update governance — carrier schema + runbook + validator gate
issue: ce-ops#277
---

**surface-bump carrier schema + runbook + validator check.**

Adds the surface-bump carrier template under carriers/ with required ratification fields and filename convention, the public surface update runbook (detect, evaluate, carrier drafting, manifest PR, canary validation, validator gate, planned fleet rollout), and registers the surfaces_bump_has_carrier validator check with unit coverage for its carrier-required and pass-through behaviour.
