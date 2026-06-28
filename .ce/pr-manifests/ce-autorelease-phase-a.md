# PR path manifest - ce-ops#315 - release-changelog W2b

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs
`verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-autorelease-phase-a`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=9abe460efaca6f708ac8f8420bc44d8167ce72b56734622fd0db27c8b2f487a2

```text
.ce/changelog/ce-autorelease-phase-a.md
.ce/pr-manifests/ce-autorelease-phase-a.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/release_changelog.py
validators/tests/unit/test_release_phase_a.py
```
