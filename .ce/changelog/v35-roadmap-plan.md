---
slug: v35-roadmap-plan
date: 2026-06-19
kind: added
scope: program planning / roadmap (docs)
issue: ce-ops#93, ce-ops#91
---

**CE v3.5 program plan — turn the flat backlog into one dependency-ordered plan to the roadmap milestone.**

- **Added `docs/v3.5-roadmap.md`** — the forward program plan: the pitch DoD
  (containerized CE + ~100 live waitlist users + usage data) and the post-pitch
  v4 horizon; **7 workstreams** that cluster every open `ce-ops`/`creator-engine`
  ticket (containment & runtime · team-mode PR throughput · install &
  pilot-readiness · secret & identity · release integrity & versioning ·
  documentation & surface · integrations & research); per-workstream goal,
  pitch-critical-vs-deferrable tag, dependencies, and a cross-workstream wave
  plan (A→D) to the pitch; a full ticket→workstream assignment table; and a
  GitHub reconciliation recommendation (milestone membership, `ws:*` labels,
  stale-open closures, two new docs tickets to file).
- **`docs/v3-roadmap.md`** — added a header pointing forward to the v3.5 plan;
  retained as the v3 historical gate-map (v3.1 pilot-ready reached).

Design-only docs; no code/behaviour change.
