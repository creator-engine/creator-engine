# PR path manifest — ce-ops#483 · Recursion bottom-out policy design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-483-bottom-out-rule-design` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=2b8ee43842d5d1b2f7d72d9dfb1a556a99765cbee210fe90f01948eec8fa209f

```text
.ce/changelog/ce-483-bottom-out-rule-design.md
.ce/pr-manifests/ce-483-bottom-out-rule-design.md
docs/design/recursion-bottom-out-policy.md
```
