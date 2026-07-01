# PR path manifest — ce-conveyor · Conveyor bundle landing

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-conveyor-bundle-landing` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=4318ac348f3186b617c2af93c05956b6795ce0a419bab43f2bf87908d9b53e8e

```text
.ce/changelog/ce-conveyor-bundle-landing.md
.ce/pr-manifests/ce-conveyor-bundle-landing.md
validators/creator_engine_validator/conveyor.py
validators/tests/unit/test_conveyor.py
```
