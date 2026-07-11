# PR path manifest — ce-n1s2-review-pickup-acting · Add default-OFF review-pickup acting chain

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref repair-n1s2-review4-dev3` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=04dcef3090d18a6653c70855f65a9665436ff25f7f6eba7ef3fa853e7cc62aae

```text
.ce/changelog/repair-n1s2-review4-dev3.md
.ce/pr-manifests/repair-n1s2-review4-dev3.md
CHANGELOG.md
deploy/systemd/ce-review-pickup-daemon.service
validators/creator_engine_validator/forge/review_acting.py
validators/creator_engine_validator/forge/review_pickup.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_review_acting.py
```
