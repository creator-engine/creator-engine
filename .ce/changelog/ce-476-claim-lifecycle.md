---
slug: ce-476-claim-lifecycle
date: 2026-07-06
kind: story
scope: claim lifecycle schema, CLI, docs, and closeout workflow
issue: ce-ops#476
---

**work_claims lifecycle seed slice.**

- Added a local claim lifecycle runtime for YAML-frontmatter claim files, including transition validation, legacy prose upgrades, listing, and structured transition logs.
- Wired `ce claim transition` and `ce claim list` into the existing claim CLI group without changing forge claim-lock commands.
- Added claim lifecycle documentation and a merge-closeout workflow that marks merged claims as `landed`.
