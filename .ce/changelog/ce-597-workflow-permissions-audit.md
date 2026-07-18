---
slug: ce-597-workflow-permissions-audit
date: 2026-07-18
kind: feature
scope: preflight workflow-permissions audit
issue: ce-ops#597
work_class: M
---

**feat(preflight): governed workflow-permissions profiles audit**

Extends the PR preflight workflow-permissions audit beyond the single
`validate.yml` no-write scan to a fail-closed, registry-driven check over every
governed workflow. Discovery now covers both `*.yml` and `*.yaml` files and the
audit recurses top-level and job-level `permissions:` blocks. A module-level
governed profile registry pins each workflow to its exact permission map, so
intentionally write-capable release and publish workflows are honored while
undeclared blocks, unratified scope expansion, and unregistered workflows are
rejected with file and YAML-path evidence. The stale-ticket reconciliation
workflow is pinned to exactly `contents: read` + `pull-requests: read`. The
registry is the ratification surface: broadening any scope or adding a workflow
requires an explicit, reviewable diff to the table. Hermetic tests cover
read-only and write-capable governed profiles plus each rejection path.
