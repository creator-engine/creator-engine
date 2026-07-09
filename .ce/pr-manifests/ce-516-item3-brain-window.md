# PR path manifest — ce-ops#516 · Correct autoclose fail-closed evidence

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-516-item3-brain-window` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=312b747e1a1f9cb15bc83d6fd7c0249a41168a054eabd000c0800edd52029482

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-516-item3-brain-window.md
.ce/pr-manifests/ce-516-item3-brain-window.md
.github/workflows/ce-ops-autoclose.yml
validators/tests/unit/test_ce_brain_drift.py
```
