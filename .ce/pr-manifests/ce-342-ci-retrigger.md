# PR path manifest - ce-ops#342 - CI re-trigger on PR body edits

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

Per-file purpose:
- **`.ce/changelog/ce-342-ci-retrigger.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-342-ci-retrigger.md`** *(A)* - this carrier.
- **`.github/workflows/validate.yml`** *(M)* - include `edited` in pull request trigger activity types.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=49013d55d3878bd02df9d723402e62172ad54e42a2ad322244abf47fde8d2c6c

```text
.ce/changelog/ce-342-ci-retrigger.md
.ce/pr-manifests/ce-342-ci-retrigger.md
.github/workflows/validate.yml
```
