# PR path manifest — ce-ops#238 · isolate herdr steer locks under xdist

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce238-herdr-xdist-isolation-hotfix` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=722c54ffee43a6b5a8dd3eeb04de0b5dcfa80f3a19b5df5ceb02d104474c50ca

```text
.ce/changelog/ce238-herdr-xdist-isolation-hotfix.md
.ce/pr-manifests/ce238-herdr-xdist-isolation-hotfix.md
validators/creator_engine_validator/runner/herdr_session.py
validators/tests/unit/test_herdr_session.py
```
