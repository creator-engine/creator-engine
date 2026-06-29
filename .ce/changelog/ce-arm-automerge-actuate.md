---
slug: ce-arm-automerge-actuate
date: 2026-06-29
kind: story
scope: Live caller wiring for the gated automerge actuator while run_mode remains dormant.
issue: ce-ops#313
---

**ARM-A automerge actuation wiring.**

- Wired a workflow_run automerge actuation caller that downloads the decision artifact and delegates to the existing gated actuator.
- Added standalone python -m caller coverage for dev-mode Dormant behavior plus predicate-gated mutation.
- Bound automerge required_checks to Validate governance artifacts without arming any state.
