# PR path manifest — ce-ops#453 · signed artifact hash-pin validate-pr guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-453a-hash-pin-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=dc8cddcca768e933436836c09dcf2df4b45f8b8239f831ec8b5751b6f624a42d

```text
.ce/changelog/ce-453a-hash-pin-guard.md
.ce/pr-manifests/ce-453a-hash-pin-guard.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/signed_artifact_pins.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_signed_artifact_pins.py
```
