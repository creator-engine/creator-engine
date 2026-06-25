---
slug: ce-ops-249-remove-roadmap-paths
date: 2026-06-25
kind: docs
scope: ce-ops
issue: ce-ops#249
---

**fully remove internal roadmap paths from public repo.**

Remove the internal v3/v3.5 roadmap files from the public repo entirely.

- Delete `docs/v3-roadmap.md` and `docs/v3.5-roadmap.md` (the PR #466 tombstones). Content is preserved privately in `creator-engine/ce-ops` under `roadmaps/`.
- De-link every reference so nothing dangles: README, the `docs/architecture/*` set (README, cockpit, pilot-deployment-transport, pilot-roadmap, pilot-uiux-model, session-status-line, shaping-ux, stage-vocabulary), `docs/guide/pilot-runbook.md`, and the `docs/index.html` doc-card. Each now points at the README Current Status section / `git log` instead.
- Website versioning policy: snapshot the outgoing live bytes to `site-archive/index-v8-1-full-automation-headline.html` + add the v8.2 ledger row (and correct the v8.1 row, which had been left pointing at the live page with no byte snapshot).
- Drop `v3.5-roadmap.md` from the docs-nav test expected-links set.
