---
slug: ce-431-launch-preflight-diagnostic
date: 2026-07-05
kind: added
scope: validators/creator_engine_validator (launch_runtime, ce_cli) + CLI reference
issue: ce-ops#431
---

**ce launch --preflight gate-diagnostic mode.**

- Added `ce launch --preflight` / `ce hud --preflight` to evaluate launch pre-spawn gates without sentinel writes, seat-surface archive/rename, tmux creation, ledger writes, or runtime/container launch.
- Shared live launch gate evaluators with the diagnostic path for harness governance, runtime-policy/resource parsing, seat-surface reuse, and resource-bounding refusal messages.
- Regenerated the committed CLI reference for the new launch flag.
