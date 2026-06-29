# PR path manifest — ce-brief:ce-nitzan-e2e-onboarding-verify-dev1 · Fix Mac container onboarding order

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-onboarding-doc-drift-fix` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=814cd7fbaa6dfb353f4c56cf700dce675021aa82ba1e4d4d4d015363912e7290

```text
.ce/changelog/ce-onboarding-doc-drift-fix.md
.ce/pr-manifests/ce-onboarding-doc-drift-fix.md
CHANGELOG.md
docs/guide/onboarding-macos-container.md
```
