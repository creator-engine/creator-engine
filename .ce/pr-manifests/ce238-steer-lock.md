# PR path manifest — ce238-steer-lock

CI runs verify-path-manifest; base..HEAD must equal the authorized set; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=06b3d45b676d1e1275959446c22f8fc541190a390c270698ed4ceb41a607cf69

```text
.ce/changelog/ce238-steer-lock.md
.ce/pr-manifests/ce238-steer-lock.md
validators/creator_engine_validator/runner/herdr_session.py
validators/tests/unit/test_herdr_session.py
```
