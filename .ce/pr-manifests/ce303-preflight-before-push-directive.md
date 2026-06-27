# PR path manifest — ce-ops#303 · propagate full-preflight-before-push standing directive to dev fleet

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce303-preflight-before-push-directive` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=5d543c0c11614ff81122b5ee63fdb06d4a2b6e2f90195b24fcd7448bdfcf6413

```text
.ce/changelog/ce303-preflight-before-push-directive.md
.ce/pr-manifests/ce303-preflight-before-push-directive.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
playbooks/controller/briefs/dispatch.md
```
