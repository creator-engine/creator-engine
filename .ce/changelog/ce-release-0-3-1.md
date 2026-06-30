---
slug: ce-release-0-3-1
date: 2026-06-30
kind: added
scope: 0.3.1 release publish
issue: ce-ops#035
---

**bump 0.3.0 → 0.3.1 + publish release mirror (spec-kit retirement).**

- Bump validators to 0.3.1 (pyproject, version.py, baked _version.py @ daded5023)
- Publish docs/downloads/0.3.1/ offline wheelhouse (CE wheel includes #678 test-coupling gate + #680 artifacts fix)
- Placeholder-signed docs/llms-install.md 0.3.1 install spec (Operator signs ce-root-v1 post-review)
- onboard_apply_live.py uv mirror URL 0.3.0 → 0.3.1
