# PR path manifest — ce-ops#364 · retire spec-kit — amend constitution Principle X (CE-Native Spec Substrate)

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-speckit-retire-principle-x` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=d2fa60d4ee3b574f0e2c7937d49c6a0ae987f5cae3cefbf7c23c6a9764c10ac0

```text
.ce/changelog/ce-speckit-retire-principle-x.md
.ce/pr-manifests/ce-speckit-retire-principle-x.md
.specify/memory/constitution.md
specs/006-retire-speckit-principle-x/plan.md
specs/006-retire-speckit-principle-x/spec.md
specs/006-retire-speckit-principle-x/tasks.md
```
