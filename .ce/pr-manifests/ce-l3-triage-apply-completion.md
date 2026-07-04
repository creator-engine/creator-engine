# PR path manifest — ce-ops#67 · L3 triage apply-mode completion

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l3-triage-apply-completion` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=8c365e741c1da41abb93b01322e664187139f4eabb224fefad805a2fa7172ccc

```text
.ce/changelog/ce-l3-triage-apply-completion.md
.ce/pr-manifests/ce-l3-triage-apply-completion.md
.github/workflows/ce-ops-triage-queue.yml
validators/creator_engine_validator/ce_ops_triage_queue.py
validators/tests/unit/test_ce_ops_triage_queue.py
```
