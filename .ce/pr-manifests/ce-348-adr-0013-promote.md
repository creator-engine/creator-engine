# PR path manifest — ce-ops#348 · ratify + promote ADR-0013 (substrate-independent authority) and harden the public-docs confidentiality gate

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-348-adr-0013-promote` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=f1407c80c2535db2e29fbe0b9c38506c2291f697d97275538d1d122d55759a99

```text
.ce/changelog/ce-348-adr-0013-promote.md
.ce/pr-manifests/ce-348-adr-0013-promote.md
docs/decisions/ADR-0013-substrate-independent-authority.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_public_docs_confidentiality.py
```
