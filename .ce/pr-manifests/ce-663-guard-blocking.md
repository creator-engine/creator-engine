# PR path manifest — ce-ops#364 · Make install-spec signature guard blocking

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-663-guard-blocking` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=337d2d6e73914850272e807426e6b50c661a56155e3438c29d6aac2fa10a9292

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-663-guard-blocking.md
.ce/pr-manifests/ce-663-guard-blocking.md
.github/workflows/validate.yml
validators/creator_engine_validator/checks/install_spec_signature_guard.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_install_spec_signature_guard.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_work_sizing_floor_ci_wiring.py
```
