# PR path manifest — ce-329 · Draft Agile/SCRUM to CE SDLC onboarding guide

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-329-scrum-to-ce-guide` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=78049198de2b2c39351e159165587b114fe9be232fbb85e842e50ba2c41ed7b6

```text
.ce/changelog/ce-329-scrum-to-ce-guide.md
.ce/pr-manifests/ce-329-scrum-to-ce-guide.md
docs/guide/agile-to-ce-sdlc.md
```
