# PR path manifest — pilot-docs-audit-20260703 · Pilot-facing command-surface corrections + collaborator section

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-pilot-docs-daytoday` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=c1203942b232df0de754afb88bd1bcf3e326b981829db86868b83c8b6a80e68d

```text
.ce/changelog/ce-pilot-docs-daytoday.md
.ce/pr-manifests/ce-pilot-docs-daytoday.md
```
