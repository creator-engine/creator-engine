# PR path manifest — L7/day-arc · Add release parity promotion gate

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l7e-parity` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=8f94e10a321d5cfa4366fc443182e3387ebadcf8e70128731532983102e55db2

```text
.ce/changelog/ce-l7e-parity.md
.ce/pr-manifests/ce-l7e-parity.md
.github/workflows/release-parity.yml
validators/tests/unit/test_release_parity_workflow.py
```
