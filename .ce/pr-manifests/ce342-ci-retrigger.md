# PR path manifest - ce-ops#342 - CI re-trigger on PR body edits

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

Per-file purpose:
- **`.ce/changelog/ce342-ci-retrigger.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce342-ci-retrigger.md`** *(A)* - this carrier.
- **`.github/workflows/validate.yml`** *(M)* - include `edited` in pull request trigger activity types.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=a2ce74edd6e4d3f9d4aaa3079bbf66af1b0fb10276ca7adeaa3765da38e12ce9

```text
.ce/changelog/ce342-ci-retrigger.md
.ce/pr-manifests/ce342-ci-retrigger.md
.github/workflows/validate.yml
```
