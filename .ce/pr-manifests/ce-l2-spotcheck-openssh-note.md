# PR path manifest — ce-ops#197 · getting-started: openssh-client prerequisite note

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l2-spotcheck-openssh-note` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=87ba51e4d753b895002f2cf0875e7fb21ed5b8066c39654648a73777207a918a

```text
.ce/changelog/ce-l2-spotcheck-openssh-note.md
.ce/pr-manifests/ce-l2-spotcheck-openssh-note.md
docs/guide/getting-started-step-by-step.md
```
