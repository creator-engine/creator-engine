# PR path manifest — none · feat(daemons): review-pickup heartbeat adoption (S3)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-daemon-heartbeat-review-s3` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=9851f40ecb1719009a25e71330ad68645645a72a791a30fa2bcb04cadd6f22e0

```text
.ce/changelog/ce-daemon-heartbeat-review-s3.md
.ce/pr-manifests/ce-daemon-heartbeat-review-s3.md
deploy/systemd/ce-review-pickup-daemon.service
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_review_pickup.py
```
