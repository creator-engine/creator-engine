# PR path manifest — ce-ops#460 · Normalize surface digest case and reject manifest-list child digest residue

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-460-digest-case-placeholder-residue` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=78a3042a036e2063ecc13217f0cfc633157a4b9082c0ef3f4f5c7819300ef281

```text
.ce/changelog/ce-460-digest-case-placeholder-residue.md
.ce/pr-manifests/ce-460-digest-case-placeholder-residue.md
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_surfaces_manifest.py
```
