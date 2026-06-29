# PR path manifest — ce-ops#364 · Add advisory install-spec signature guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-364-install-sig-ci-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=461b3285f33d58425880ceb01951f9d4540094e9327dd66531e95c3c13295067

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-364-install-sig-ci-guard.md
.ce/pr-manifests/ce-364-install-sig-ci-guard.md
.github/workflows/validate.yml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/install_spec_signature_guard.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_install_spec_signature_guard.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_work_sizing_floor_ci_wiring.py
```
