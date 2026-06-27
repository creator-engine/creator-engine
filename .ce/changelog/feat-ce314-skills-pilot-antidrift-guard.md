---
slug: feat-ce314-skills-pilot-antidrift-guard
date: 2026-06-27
kind: feature
scope: Playbooks→Skills HYBRID pilot — ce-dispatch + ce-merge-gate skills + skill_antidrift_guard CI check
issue: ce-ops#318
---

**Playbooks→Skills slice 1 — ce-dispatch + ce-merge-gate pilot + anti-drift guard.**

First slice of the Playbooks→Skills HYBRID pilot (EPIC ce-ops#314): the ce-dispatch skill (thin pointer to playbooks/controller/briefs/dispatch.md plus the pointer+SHA dispatch mechanic), the ce-merge-gate skill (checklist-only, disable-model-invocation, zero mutating forge command), and skill_antidrift_guard — a registered CI check asserting every CE action-skill references an in-tree SSOT and embeds no mutating forge command, with tests proving the guard has teeth. Internal controller ergonomics only; not shipped in the public command set. Governance stays on the PreToolUse hook seam, never on skill frontmatter.
