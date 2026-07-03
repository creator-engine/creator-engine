# PR path manifest — ce-ops#294 · Press-merge evidence bundle v1

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-294-press-merge-bundle` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** epic

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=2c806bf80a366045d5ca8f4cc29ff7d401bece9e6c5771cf559f71ab87f6202d

```text
.ce/changelog/ce-294-press-merge-bundle.md
.ce/pr-manifests/ce-294-press-merge-bundle.md
.github/workflows/automerge-decide.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/press_merge_evidence.py
validators/creator_engine_validator/schemas/ce-press-merge-evidence-bundle.v1.json
validators/tests/unit/test_press_merge_evidence.py
```
