---
slug: ce-onboard-didyoumean-guard
date: 2026-07-05
kind: fixed
scope: ce onboard CLI
work_class: tiny
---

**Hint installer-only flags to `ce install`.**

- Refuse stale installer-flow flags passed to native `ce onboard` with exit 2 and a stderr hint to rerun the same arguments under `ce install`.
- Keep native `ce onboard` dispatch unchanged for first-run orchestrator flags.
