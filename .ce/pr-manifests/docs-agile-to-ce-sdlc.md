# PR path manifest — creator-engine/ce-ops#329 · Agile/SCRUM to CE spec-driven SDLC onboarding guide

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref docs-agile-to-ce-sdlc` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=c7c9dbf4fc69b8f24c80c7662fc67bbcf9a95a77b82b17b7643f040abf22cce5

```text
.ce/changelog/docs-agile-to-ce-sdlc.md
.ce/pr-manifests/docs-agile-to-ce-sdlc.md
docs/guide/agile-to-ce-sdlc.md
docs/guide/welcome.md
```
