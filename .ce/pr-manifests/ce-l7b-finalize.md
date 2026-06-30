# PR path manifest — L7/day-arc · Finalize signed release publish workflow

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l7b-finalize` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=be8f987f2c68a9dc1c060cf9107b815bae2ed82edf6ee4ffaec407ae08fde772

```text
.ce/changelog/ce-l7b-finalize.md
.ce/pr-manifests/ce-l7b-finalize.md
.github/workflows/release-finalize.yml
validators/tests/unit/test_release_finalize_workflow.py
```
