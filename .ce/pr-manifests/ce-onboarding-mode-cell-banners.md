# PR path manifest — ce-ops#673 · Add Solo+Dev and Solo+CEO onboarding guides with scope-mode cell banners

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-onboarding-mode-cell-banners` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=81f732c5a11847adae0b3d8804d74488cad7d72fa42e53b057670a16ab8e915c

```text
.ce/changelog/ce-onboarding-mode-cell-banners.md
.ce/pr-manifests/ce-onboarding-mode-cell-banners.md
docs/guide/agile-to-ce-sdlc.md
docs/guide/getting-started-step-by-step.md
docs/guide/solo-ceo-onboarding.md
docs/guide/solo-dev-onboarding.md
docs/index.html
```
