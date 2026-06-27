# PR path manifest — ce-ops#330 · Beginner step-by-step getting-started walkthrough

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref docs-getting-started-step-by-step` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e7ebaae4dcb977a1c0a4a20f0d61e45d8b98a643de6226ecf6660e464f435193

```text
.ce/changelog/docs-getting-started-step-by-step.md
.ce/pr-manifests/docs-getting-started-step-by-step.md
docs/guide/getting-started-step-by-step.md
docs/guide/welcome.md
```
