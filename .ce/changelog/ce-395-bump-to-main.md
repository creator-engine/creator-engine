---
slug: ce-395-bump-to-main
date: 2026-07-02
kind: changed
scope: release
issue: ce-ops#395
---

**Add release-bump commit mode.**

- Add release-bump commit mode that creates a fresh local branch, commits only canonical version sources, and generates PR carriers without pushing or opening a PR.
- Delete the orphaned release_orchestrate module.
