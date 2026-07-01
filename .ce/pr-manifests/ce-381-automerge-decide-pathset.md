# PR path manifest - ce-ops#381 · automerge decide PR path-set

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-381-automerge-decide-pathset` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=7009720e3cff73b13b181d722e1cfecb5fa7d420249efc946654bafcd1cbba71

```text
.ce/changelog/ce-381-automerge-decide-pathset.md
.ce/pr-manifests/ce-381-automerge-decide-pathset.md
.github/workflows/automerge-decide.yml
validators/tests/unit/test_automerge_policy.py
```
