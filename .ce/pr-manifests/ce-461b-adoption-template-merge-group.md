# PR path manifest — 461 · adoption workflow template merge_group trigger parity

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-461b-adoption-template-merge-group` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=7fc64c5a7e2cbd2a474975ae5e211104e508a3f7921bbb5124796b2955969d52

```text
.ce/changelog/ce-461b-adoption-template-merge-group.md
.ce/pr-manifests/ce-461b-adoption-template-merge-group.md
validators/creator_engine_validator/onboard_apply.py
validators/tests/unit/test_onboard_apply.py
```
