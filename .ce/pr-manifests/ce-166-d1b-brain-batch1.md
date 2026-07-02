# PR path manifest — ce-166 · D1b brain migration batch 1

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-166-d1b-brain-batch1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** L

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=b2abb71665b4168e119f7aca4794484fd5bc35bd592307e59b4ed094bc6ebce7

```text
.ce/brain/assertions.yaml
.ce/brain/doctrine-coverage.yaml
.ce/changelog/ce-166-d1b-brain-batch1.md
.ce/pr-manifests/ce-166-d1b-brain-batch1.md
validators/tests/unit/test_ce_brain_drift.py
```
