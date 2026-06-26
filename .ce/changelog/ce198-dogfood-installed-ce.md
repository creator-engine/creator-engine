---
slug: ce198-dogfood-installed-ce
date: 2026-06-26
kind: added
scope: validator engine installed CE dogfood entrypoints
issue: ce-ops#198
---

**Dogfood installed CE console scripts for belt and lane entrypoints.**

- Default the pickup belt lane-launch seam to `ce lane launch`, with
  `CE_LANE_LAUNCH_BIN` / `CE_BIN` compatibility overrides for source-checkout
  fallback.
- Treat `cev3` as part of the locked packaging console-script contract for
  merge-queue belt polling.
- Add `ce doctor --require-installed-ce` to deterministically refuse source
  checkout / `python -m` posture when installed-CE dogfood is required.
- Add a short migration runbook for repointing belt crons and lane launches to
  installed `ce` / `cev3`.
