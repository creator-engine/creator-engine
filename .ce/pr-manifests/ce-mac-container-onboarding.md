# PR path manifest — story · macOS container onboarding runbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-mac-container-onboarding` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=4bc9ab3eba1da9d5d0a4c9a031ae9211adabcb2afec809d597165bdf295d0e48

```text
.ce/changelog/ce-mac-container-onboarding.md
.ce/pr-manifests/ce-mac-container-onboarding.md
docs/guide/onboarding-macos-container.md
docs/guide/welcome.md
```
