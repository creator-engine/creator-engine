# PR path manifest — ce-ops#354 · support corpus contributing docs scrub

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-corpus-scrub-contributing` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=114a7cfba372e4417cbf1da09466444bd0376dbbc38da32fcfab7aa136594ccd

```text
.ce/changelog/ce-corpus-scrub-contributing.md
.ce/pr-manifests/ce-corpus-scrub-contributing.md
docs/contracts/playbook-format.md
docs/guide/contributing-to-ce.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/creator_engine_validator/support_corpus_allowlist.yaml
validators/tests/unit/test_support_agent_p0.py
validators/tests/unit/test_support_agent_phase1.py
```
