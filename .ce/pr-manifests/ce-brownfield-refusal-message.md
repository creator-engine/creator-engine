# PR path manifest — ce-brownfield-refusal-message · Distinguish brownfield adoption credential-resolution refusals

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-brownfield-refusal-message` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=5b117f5d4a5e9e199d4e4ab7030f5a8652600a89b8804c72322613f1041748c0

```text
.ce/changelog/ce-brownfield-refusal-message.md
.ce/pr-manifests/ce-brownfield-refusal-message.md
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_v3_brownfield_refusals.py
```
