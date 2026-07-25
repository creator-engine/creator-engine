---
slug: ce652-runsc-image-check-honesty
date: 2026-07-25
kind: fixed
scope: VPS runsc manifest consistency validation
issue: ce-ops#652
---

**Make VPS runsc image-consistency validation non-vacuous.**

- Replace the obsolete VPS shell-default scan with checks that the launcher
  resolves its default image from the manifest and carries no digest literal.
- Retain the shared shell-default comparison for DGX, where its image default
  still exists and remains independently covered.
- Cover resolver removal, digest literal reintroduction, and duplicate VPS
  manifest entries as fail-closed refusals.
