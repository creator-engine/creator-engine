# PR path manifest — ce-docs-quickstart-step-numbering · Renumber quickstart steps

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-docs-quickstart-step-numbering` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=da6ede059954f8ae8a43349628ddc107bcde4c427727a6aa6c9bfaef37060253

```text
.ce/changelog/ce-docs-quickstart-step-numbering.md
.ce/pr-manifests/ce-docs-quickstart-step-numbering.md
docs/guide/zero-to-governed-seat-quickstart.md
```
