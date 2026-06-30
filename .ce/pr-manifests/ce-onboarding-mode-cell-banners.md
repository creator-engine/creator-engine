# PR path manifest — ce-ops#673 · Add Solo+Dev scope banners and Solo+CEO onboarding guide

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-onboarding-mode-cell-banners` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=5b9aa8207385af2d54405e4dca5ee79ff050a79669eb4d1259c71d7123db8ad4

```text
.ce/changelog/ce-onboarding-mode-cell-banners.md
.ce/pr-manifests/ce-onboarding-mode-cell-banners.md
docs/guide/agile-to-ce-sdlc.md
docs/guide/getting-started-step-by-step.md
docs/guide/solo-ceo-onboarding.md
docs/index.html
```
