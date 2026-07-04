# PR path manifest — ce-ops#438 · Complete Walkthrough public guide

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-438-complete-walkthrough` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=b27524de3acc7f542564919717f43095ab38112e4bb2403715767dcbcc43959b

```text
.ce/changelog/ce-438-complete-walkthrough.md
.ce/pr-manifests/ce-438-complete-walkthrough.md
docs/guide/complete-walkthrough.html
docs/guide/complete-walkthrough.md
docs/guide/getting-started-step-by-step.md
docs/guide/solo-ceo-onboarding.html
docs/guide/solo-ceo-onboarding.md
docs/guide/welcome.md
docs/index.html
validators/tests/unit/test_site_index_docs_nav.py
```
