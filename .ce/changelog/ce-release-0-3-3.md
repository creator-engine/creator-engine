---
slug: ce-release-0-3-3
date: 2026-07-06
kind: chore
scope: release
issue: creator-engine/ce-ops#469
---

**bump 0.3.2 -> 0.3.3 + CHANGELOG + release staging.**

Minimal point release to unblock canary C and the Arad live tenant. Bumps version 0.3.2 -> 0.3.3, fixes uv mirror URL drift in onboard_apply_live, rolls up six changelog fragments merged since 0.3.2, assembles the 0.3.3 CHANGELOG section, publishes the signed 0.3.3 install spec to docs/llms-install.md, and stages signed 0.3.3 release artifacts under .ce/release-staging/0.3.3/.
