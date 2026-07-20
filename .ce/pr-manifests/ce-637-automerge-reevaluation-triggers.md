# PR path manifest - automerge decision re-evaluation

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref
ce-637-automerge-reevaluation-triggers` and requires this PR's `base..HEAD`
diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=d89be23e659408b35c822762df0bfeb3d3b10b063ed295e8119d6499e93e2fa4

```text
.ce/changelog/ce-637-automerge-reevaluation-triggers.md
.ce/pr-manifests/ce-637-automerge-reevaluation-triggers.md
.github/workflows/automerge-decide.yml
```
