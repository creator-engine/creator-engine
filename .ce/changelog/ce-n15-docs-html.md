---
slug: ce-n15-docs-html
date: 2026-06-30
kind: docs
scope: site
issue: ce-ops#37
---

**Render public docs to HTML.**

- Render 6 public guide docs (understanding-ce, pilot-runbook, contributing-to-ce, solo-dev-onboarding, solo-ceo-onboarding, SECURITY_MODEL) from Markdown to styled HTML pages matching the docs/index.html dark theme.
- Update docs/index.html #docs section links from .md to .html for all 6 rendered docs; llms-install.md remains raw .md (machine-fetched signed spec).
- Update validators/tests/unit/test_site_index_docs_nav.py to expect .html links.
- Cross-link strategy: published doc cross-links use rendered .html; unpublished docs inside docs/ use GitHub blob URL; paths escaping docs/ tree use repo-root blob URL.
- Product-lens scrub: all 6 source docs and rendered HTML are clean of ce-ops# ticket refs and internal host identifiers.
