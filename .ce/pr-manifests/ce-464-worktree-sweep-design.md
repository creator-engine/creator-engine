# PR path manifest — ce-ops#464 · worktree-debt classified-sweep design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-464-worktree-sweep-design` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

Scope: design only. No deletion, pruning, source implementation, validator
mutation, or live cleanup is authorized by this PR.

Per-file purpose:

- **`.ce/changelog/ce-464-worktree-sweep-design.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-464-worktree-sweep-design.md`** *(A)* - this closed path-set carrier.
- **`docs/design/worktree-debt-classified-sweep.md`** *(A)* - design document for classified worktree-debt sweep.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=2b29b634adf1649c671c734b1153a0daf64630178bd4d54bd39a81b30a2fcd18

```text
.ce/changelog/ce-464-worktree-sweep-design.md
.ce/pr-manifests/ce-464-worktree-sweep-design.md
docs/design/worktree-debt-classified-sweep.md
```
