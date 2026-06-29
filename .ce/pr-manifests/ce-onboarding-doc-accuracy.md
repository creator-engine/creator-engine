# PR path manifest — docs · Onboarding doc accuracy fix after installer smoke

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-onboarding-doc-accuracy` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=5da34d4336b159b0e7b8355383f6fd290684e6873f49706592dbfe0ec15173ed

```text
.ce/changelog/ce-onboarding-doc-accuracy.md
.ce/pr-manifests/ce-onboarding-doc-accuracy.md
README.md
docs/contracts/installer.md
docs/guide/onboarding-macos-container.md
```
