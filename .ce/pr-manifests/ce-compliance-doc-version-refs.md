# PR path manifest - ce-compliance-doc-version-refs

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-compliance-doc-version-refs` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=de9961cc9f0dc59d8461d82455680c926891a91da8e059c97d57c947c29d6221

```text
.ce/changelog/ce-compliance-doc-version-refs.md
.ce/pr-manifests/ce-compliance-doc-version-refs.md
docs/compliance/ssdf-slsa-conformance.md
```
