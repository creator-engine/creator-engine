# PR path manifest — creator-engine/ce-ops#385 · docs: update work-class authoring vocabulary

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-385-workclass-doc-vocab` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=dd60215d73a42f0865a85cf41835d1b8353348585a3cce742428ea1c07dc3f07

```text
.ce/changelog/ce-385-workclass-doc-vocab.md
.ce/pr-manifests/ce-385-workclass-doc-vocab.md
docs/contracts/work-sizing-tiers.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
```
