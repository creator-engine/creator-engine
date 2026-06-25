---
slug: ce249-readme-dangling-links
date: 2026-06-25
kind: fix
scope: docs
issue: ce-ops#249
---

**remove dangling roadmap links from README + guard dangling internal-doc links.**

Delete dead links to deleted docs/v3-roadmap.md and docs/v3.5-roadmap.md from README intro; add CI guard failing on dangling relative internal-doc links in public docs.
