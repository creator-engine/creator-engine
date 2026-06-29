# PR path manifest — ce-ops#354 · support corpus contributing docs scrub

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-corpus-scrub-contributing` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=0d663b14b1631b98bc60f21d3da8224b6c1c717ff5202fb39cbd10481be28a47

```text
.ce/changelog/ce-corpus-scrub-contributing.md
.ce/pr-manifests/ce-corpus-scrub-contributing.md
docs/contracts/playbook-format.md
docs/guide/contributing-to-ce.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/creator_engine_validator/support_corpus_allowlist.yaml
validators/tests/unit/test_support_agent_p0.py
```
