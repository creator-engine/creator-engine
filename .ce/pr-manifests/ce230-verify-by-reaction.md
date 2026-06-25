# PR path manifest — ce-ops#230 · verify brief dispatch by agent reaction

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce230-verify-by-reaction` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=b3af3cfbe4ae77c8b4aa09c9f361b1b626e6dc793083f637c81ee234a78c5424

```text
.ce/changelog/ce230-verify-by-reaction.md
.ce/pr-manifests/ce230-verify-by-reaction.md
validators/creator_engine_validator/runner/herdr_session.py
validators/tests/unit/test_herdr_session.py
```
