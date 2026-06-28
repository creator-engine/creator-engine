# PR path manifest - ce-ops#342 - CI re-trigger on PR body edits

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

Per-file purpose:
- **`.ce/brain/assertions.yaml`** *(M)* - update the pinned validate workflow hash assertion.
- **`.ce/changelog/ce-342-ci-retrigger.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-342-ci-retrigger.md`** *(A)* - this carrier.
- **`.github/workflows/validate.yml`** *(M)* - include `edited` in pull request trigger activity types.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=0efbb578252da1ba5b67375e69b2c12d6c0a7d18f6b6dc69ea9c7eb62befdee3

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-342-ci-retrigger.md
.ce/pr-manifests/ce-342-ci-retrigger.md
.github/workflows/validate.yml
```
