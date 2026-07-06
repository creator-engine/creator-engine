---
slug: ce-462-auto-tag-dispatch-chain
date: 2026-07-06
kind: fixed
scope: release automation (release-auto-tag workflow)
issue: ce-ops#462
---

**fix: release-auto-tag explicit ordered dispatch (GITHUB_TOKEN suppression).**

release-auto-tag now explicitly dispatches publish-runtime-image, publish-seat-image (gated on runtime success), and release.yml in order after pushing the annotated tag, bypassing GITHUB_TOKEN recursive-event suppression that silenced all downstream push:tags: triggers.
