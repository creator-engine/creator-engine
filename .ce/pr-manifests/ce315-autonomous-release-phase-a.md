# PR path manifest — ce-ops#315 · autonomous release Phase A (stage-to-seam)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce315-autonomous-release-phase-a` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=36e1dc1bf394879b0f2ceb51f33df316ba6d4fcfe39fabc542c3e9734f2f96d9

```text
.ce/changelog/ce315-autonomous-release-phase-a.md
.ce/pr-manifests/ce315-autonomous-release-phase-a.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/release_bump.py
validators/creator_engine_validator/release_changelog.py
validators/creator_engine_validator/release_orchestrate.py
validators/tests/unit/test_release_phase_a.py
```
