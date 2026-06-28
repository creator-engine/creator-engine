# PR path manifest - ce-ops#315 - autonomous release phase A W2c

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs
`verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-autorelease-phase-a`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=e5239aa8d1328263a79f7e89a192818656654bf2017837c7531a4a7e5c5e7cb6

```text
.ce/changelog/ce-autorelease-phase-a.md
.ce/pr-manifests/ce-autorelease-phase-a.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/release_changelog.py
validators/creator_engine_validator/release_orchestrator.py
validators/tests/unit/test_release_phase_a.py
```
