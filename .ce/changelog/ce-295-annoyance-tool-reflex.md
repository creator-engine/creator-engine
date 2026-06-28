---
slug: ce-295-annoyance-tool-reflex
date: 2026-06-28
kind: added
scope: controller playbook / session bootstrap
issue: ce-ops#295
---

**Codify the annoyance→tool reflex and replace the empty AGENTS.md stub with an agent-authored session-bootstrap policy block.**

- Added `playbooks/controller/briefs/annoyance-to-tool.md`: controller runbook
  entry that governs the loop from felt friction to filed ticket to dispatched tool.
- Added `annoyance-to-tool` stage + `annoyance-filed` gate to
  `playbooks/controller/workflow.ce.yml`.
- Replaced the SPECKIT stub in `AGENTS.md` with a real session-bootstrap policy
  block covering role definitions, dispatch discipline, and hard-stop rules —
  authored by this agent (ce-ops#295 agent-self-authoring DoD).
- Declared work class: tiny.
