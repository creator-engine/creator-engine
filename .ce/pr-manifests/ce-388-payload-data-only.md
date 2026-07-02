# PR path manifest — ce-ops#388 · Enforce ADR-0004 data-only discovery payload schema

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-388-payload-data-only` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=3b6727dcef1215a7aeb957638ab50fc6bb805a338df93e738eed25c6c0884dde

```text
.ce/changelog/ce-388-payload-data-only.md
.ce/pr-manifests/ce-388-payload-data-only.md
validators/creator_engine_validator/forge/integrator_belt.py
validators/creator_engine_validator/pickup.py
validators/creator_engine_validator/pickup_payload_schema.py
validators/tests/unit/test_pickup_payload_schema.py
```
