---
slug: ce-410-integrator-git-phase-split
date: 2026-07-03
kind: changed
scope: forge/integrator-belt
issue: ce-ops#410
---

**Split integrator git authority by phase.**

- Route local integrator git commands through LocalGitContext while fetch, push, and ls-remote retain transport credentials.
- Add regression coverage that records every git subprocess environment and rejects credential-bearing local git envs.
