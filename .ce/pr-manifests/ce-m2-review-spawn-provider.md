# PR path manifest — M2 · Governed review-acting spawn provider — core (M2 part 1)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-m2-review-spawn-provider` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=ce862bd09a86d3cce2070d30a5dd56dde3e239fea801ba2719f5603d15c9a6ec

```text
.ce/changelog/ce-m2-review-spawn-provider.md
.ce/pr-manifests/ce-m2-review-spawn-provider.md
deploy/systemd/ce-review-spawn-provider.env.example
deploy/systemd/ce-review-spawn-provider.service
validators/creator_engine_validator/forge/ratifier_queue.py
validators/creator_engine_validator/forge/review_acting.py
validators/creator_engine_validator/forge/review_spawn_provider.py
validators/tests/unit/test_ratifier_queue.py
validators/tests/unit/test_review_acting.py
validators/tests/unit/test_review_spawn_provider.py
```
