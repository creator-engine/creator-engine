# PR path manifest — ce-ops#410 · ce-ops#410 slice 10: final publish re-verification + per-phase audit

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-410-s10-publish-reverify-audit` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=6e945d415ac4e83b755fc66090d8f593e748c5eb4731b6cfb8867a86cd97892b

```text
.ce/changelog/ce-410-s10-publish-reverify-audit.md
.ce/pr-manifests/ce-410-s10-publish-reverify-audit.md
validators/creator_engine_validator/conveyor_daemon.py
validators/tests/unit/test_conveyor_daemon.py
```
