# PR path manifest — ce-ops#628 · proof-tag discipline for operator-facing claims

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-628-proof-tags` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=3b9e0fc1bacd954569ec5d0dd93ba8ee1e6e66939589e001219f12aa832a99ed

```text
.ce/changelog/ce-628-proof-tags.md
.ce/pr-manifests/ce-628-proof-tags.md
docs/operations/PROOF_TAG_DISCIPLINE.md
validators/creator_engine_validator/public_docs_confidentiality.py
```
