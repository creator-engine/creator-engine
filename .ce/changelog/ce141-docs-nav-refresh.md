---
slug: ce141-docs-nav-refresh
date: 2026-06-22
kind: changed
scope: docs site nav
issue: ce-ops#141
work_class: story
---

Refreshes the live v8 site docs navigation.

- Adds a real `#docs` section to `docs/index.html` so the nav Docs anchor lands
  on documentation instead of a missing target.
- Links the pitch-facing docs section to current user docs: signed install
  spec, understanding CE, pilot runbook, contributor guide, security model, and
  v3.5 roadmap.
- Adds a focused offline unit test proving every same-page `#anchor` href in
  the site resolves to an element id and that the docs section links to real
  tracked Markdown docs.
