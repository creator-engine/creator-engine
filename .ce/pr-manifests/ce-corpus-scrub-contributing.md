# PR path manifest — ce-ops#354 · support corpus contributing docs scrub

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-corpus-scrub-contributing` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=492074cd239f34a7e6c6131dd9811aa0b845fd8a72193266d78ca4727c4721b8

```text
.ce/changelog/ce-corpus-scrub-contributing.md
.ce/pr-manifests/ce-corpus-scrub-contributing.md
docs/contracts/playbook-format.md
docs/guide/contributing-to-ce.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/creator_engine_validator/support_corpus_allowlist.yaml
```
