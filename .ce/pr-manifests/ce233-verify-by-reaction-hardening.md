# PR path manifest — ce-ops#233 · harden verify-by-reaction

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce233-verify-by-reaction-hardening` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=56cd700aa09c71bddd59369ad84280b5bbc74d61e8bee0726c0de1bff036e9b4

```text
.ce/changelog/ce233-verify-by-reaction-hardening.md
.ce/pr-manifests/ce233-verify-by-reaction-hardening.md
validators/creator_engine_validator/runner/herdr_session.py
validators/tests/unit/test_herdr_session.py
```
