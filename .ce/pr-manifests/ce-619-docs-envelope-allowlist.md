# PR path manifest — ce-ops#619 · docs_envelope extension allow-list

This per-PR carrier lists the closed authorized path set for the `S` slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=b726452419284880e3e8628816acc38c99ac1c306e7c9cc7c685881b3082ae1f

```text
.ce/changelog/ce-619-docs-envelope-allowlist.md
.ce/pr-manifests/ce-619-docs-envelope-allowlist.md
validators/creator_engine_validator/forge/automerge_policy.py
validators/tests/unit/test_automerge_policy.py
```
