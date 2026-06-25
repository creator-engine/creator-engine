# PR path manifest — ce-ops#191 · point governed-flow docs at cev3 + curl/git prereq (N2)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce191-n2-docs-cev3-quickstart` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=ea17d204e130bec7f07c8b5ef82037b956c14054ad7d3136002e30998cd49d53

```text
.ce/changelog/ce191-n2-docs-cev3-quickstart.md
.ce/pr-manifests/ce191-n2-docs-cev3-quickstart.md
docs/guide/pilot-runbook.md
docs/guide/zero-to-governed-seat-quickstart.md
docs/operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md
```
