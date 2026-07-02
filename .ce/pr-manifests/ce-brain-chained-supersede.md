# PR path manifest — ce-brain-chained-supersede · Chained brain assertion supersedes

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-brain-chained-supersede` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=4b014b5ffa06856e04c1768689d05e6cd4ba06b2cb2627630a30f359ba187b8b

```text
.ce/changelog/ce-brain-chained-supersede.md
.ce/pr-manifests/ce-brain-chained-supersede.md
validators/creator_engine_validator/brain_runtime.py
validators/tests/unit/test_brain_runtime.py
```
