# PR path manifest — ce-ops#37 · Render public docs to HTML

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-n15-docs-html` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=59eb3f1591b13556adbd8cf91ed7d3fa03be4bea6bd6992723d072a20214e2a1

```text
.ce/changelog/ce-n15-docs-html.md
.ce/pr-manifests/ce-n15-docs-html.md
docs/guide/contributing-to-ce.html
docs/guide/pilot-runbook.html
docs/guide/solo-ceo-onboarding.html
docs/guide/solo-dev-onboarding.html
docs/guide/understanding-ce.html
docs/index.html
docs/security/SECURITY_MODEL.html
validators/tests/unit/test_site_index_docs_nav.py
```
