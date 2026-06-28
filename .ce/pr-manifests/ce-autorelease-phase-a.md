# PR path manifest - ce-ops#315 - autonomous release phase A W2d

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs
`verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-autorelease-phase-a`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=07e24ed916a18e5b3e4630ff821636409e9caa5c0ca009ac092e2ec50f9f9315

```text
.ce/changelog/ce-autorelease-phase-a.md
.ce/pr-manifests/ce-autorelease-phase-a.md
.github/workflows/release.yml
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/release_bump.py
validators/creator_engine_validator/release_changelog.py
validators/creator_engine_validator/release_orchestrator.py
validators/tests/unit/test_release_phase_a.py
validators/tests/unit/test_release_workflow.py
```
