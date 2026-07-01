# PR path manifest — ce-ops#703 · CI run block injection guard test

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-ci-runblock-injection-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** tiny

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=bb512f7dfb19f17d282439923926ded6b7249e7e71aec51815959da55f235f5e

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-ci-runblock-injection-guard.md
.ce/pr-manifests/ce-ci-runblock-injection-guard.md
.github/workflows/validate.yml
validators/tests/unit/test_work_sizing_floor_ci_wiring.py
validators/tests/unit/test_workflow_no_runblock_injection.py
```
