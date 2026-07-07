# PR path manifest — ce-ops#485 · Canonical CE journey doc pair

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-485-canonical-journey-doc-pair` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=23

AUTHORIZED_PATHS_SHA256=f4b7b151c8552ae3534ab16501b7582e6cae9acda01667ff7f65952457187a90

```text
.ce/changelog/ce-485-canonical-journey-doc-pair.md
.ce/pr-manifests/ce-485-canonical-journey-doc-pair.md
docs/guide/agile-to-ce-sdlc.md
docs/guide/complete-walkthrough.html
docs/guide/complete-walkthrough.md
docs/guide/contributing-to-ce.html
docs/guide/contributing-to-ce.md
docs/guide/how-ce-builds-software.html
docs/guide/how-ce-builds-software.md
docs/guide/pilot-runbook.html
docs/guide/pilot-runbook.md
docs/guide/quickstart.html
docs/guide/quickstart.md
docs/guide/solo-ceo-onboarding.html
docs/guide/solo-ceo-onboarding.md
docs/guide/solo-dev-onboarding.html
docs/guide/solo-dev-onboarding.md
docs/guide/understanding-ce.html
docs/guide/understanding-ce.md
docs/guide/welcome.md
docs/index.html
docs/llms.txt
validators/tests/unit/test_site_index_docs_nav.py
```
