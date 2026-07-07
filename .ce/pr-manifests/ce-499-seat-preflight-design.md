# PR path manifest — ce-ops#499 · Seat-side preflight design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-499-seat-preflight-design` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=18aa1b84b7f728fdfbcccd7b039de05e41bba2b14bcbac3b13e62900def6c3e5

```text
.ce/changelog/ce-499-seat-preflight-design.md
.ce/pr-manifests/ce-499-seat-preflight-design.md
docs/design/seat-side-preflight.md
```
