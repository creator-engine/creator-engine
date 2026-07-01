# PR path manifest — ce-contributing-guide-ci-steps · Document first-PR CI steps in the contributing guide

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-contributing-guide-ci-steps` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=981742328593e01dc5a9cfee6277e19f8ab3048ddc1b8e6297fd3f862b2a045b

```text
.ce/changelog/ce-contributing-guide-ci-steps.md
.ce/pr-manifests/ce-contributing-guide-ci-steps.md
docs/guide/contributing-to-ce.html
docs/guide/contributing-to-ce.md
```
