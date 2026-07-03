# PR path manifest — pilot-docs-audit-20260703 · Pilot-facing command-surface corrections + collaborator section

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-pilot-docs-daytoday` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=3323e66ef72129c5bf5ffd9e027d605b6fc66dfca391efc9710e96a6a3c1a6c3

```text
.ce/changelog/ce-pilot-docs-daytoday.md
.ce/pr-manifests/ce-pilot-docs-daytoday.md
docs/guide/solo-ceo-onboarding.md
docs/guide/solo-dev-onboarding.md
docs/index.html
```
