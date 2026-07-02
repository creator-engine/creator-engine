# PR path manifest — ce-ops#403 · Harden public docs confidentiality scanner

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-403-scanner-hardening` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=e6045ffbc9e3ee3d8d201b9fee346efcd8793ea548ae6f07c595a204c8374c0a

```text
.ce/changelog/ce-403-scanner-hardening.md
.ce/pr-manifests/ce-403-scanner-hardening.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_public_docs_confidentiality.py
validators/tests/unit/test_public_docs_confidentiality_cli.py
```
