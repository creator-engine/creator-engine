---
slug: ce-l7a-auto-tag
date: 2026-06-30
kind: added
scope: release automation
issue: L7-a
---

**Add automatic release tag workflow.**

- Adds a main-push workflow that reads the validator version source with AST parsing and creates an annotated release tag only for stable semver versions.
- Adds static contract coverage for tag absence checks, non-semver skips, and contents write permission.
