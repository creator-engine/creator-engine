---
slug: ce248-playbook-run
date: 2026-06-25
kind: feat
scope: ce-ops
issue: ce-ops#248
---

Add `ce playbook list`, `ce playbook show`, and fail-closed `ce playbook run --dry-run`
for public dual-use `PLAYBOOK.md` files. Public frontmatter validates against the
documented format, projects deterministically into the existing internal
`ce-playbook` descriptor schema, and validates that projection with the existing
schema helper before any CLI output.
