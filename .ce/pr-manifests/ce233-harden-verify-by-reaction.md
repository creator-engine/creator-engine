# PR path manifest - ce-ops#233 - harden verify-by-reaction

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce233-harden-verify-by-reaction` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=0a6186635a443a00095c5f20d158ec3f32b8c893f0814be9b0e368207dd60ec7

```text
.ce/changelog/ce233-harden-verify-by-reaction.md
.ce/pr-manifests/ce233-harden-verify-by-reaction.md
validators/creator_engine_validator/runner/herdr_session.py
validators/tests/unit/test_herdr_session.py
```
