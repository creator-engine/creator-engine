# PR path manifest - ce80-signed-publish - deterministic signed-release staging pipeline

Per-PR carrier (`.ce/pr-manifests/<branch_slug(head_ref)>.md`, the ce-ops#21
convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce80-signed-publish
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path set
below. This carrier lists itself.

Work class:
Feature. This adds a new release staging command and helper with focused tests,
but does not publish live artifacts, create tags, or automate root signing.

Base:
`b58b136af037cd045d3326e50900e538fa24d2e2` (`origin/main` at branch creation).

The change:
- Adds `release_publish.stage_signed_release(...)`, a deterministic pipeline
  helper that stages a Pages mirror from an explicit source commit and version.
- Wires `creator-engine-validator release-stage` with explicit output, forced
  replacement, dry-run, and placeholder-only signing mode.
- Stops before `ce-root-v1` signing by writing `<RESIGN-REQUIRED-ce-root-v1>` and
  the Operator's `ssh-keygen -Y sign` invocation.
- Tests deterministic output, idempotency, parity fail-closed behavior, staged
  hash fail-closed behavior, and the signing seam.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=811da00cfb2f5a85d4f59f035045a3090beaa91b0fe495dadf319e84b6fbc589

```text
.ce/changelog/ce80-signed-publish.md
.ce/pr-manifests/ce80-signed-publish.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/release_publish.py
validators/tests/unit/test_release_publish.py
```
