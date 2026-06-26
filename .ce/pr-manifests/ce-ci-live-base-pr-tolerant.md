# PR path manifest — ce-ci-live-base-pr-tolerant · live-comparison base tolerant of behind PRs

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-ci-live-base-pr-tolerant` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

- **Declared work class:** tiny

This PR legitimately touches `.github/workflows/` — the merge-gate CI workflow
is the surface under change (relaxing a `pull_request`-context hard-fail).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=ca3e18c10e3286b1623136cc93f6b0f4a9116155931ecd13f2aad89aebd92a83

```text
.ce/changelog/ce-ci-live-base-pr-tolerant.md
.ce/pr-manifests/ce-ci-live-base-pr-tolerant.md
.github/workflows/validate.yml
```
