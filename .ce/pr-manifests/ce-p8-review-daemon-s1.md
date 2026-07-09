---
slug: ce-p8-review-daemon-s1
declared_work_class: story
---

# PR path manifest - P8 review-pickup dry-run daemon slice 1

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-p8-review-daemon-s1` and requires
this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this
carrier lists itself.

Acceptance-Evidence: validators/tests/unit/test_p8_review_daemon_s1.py

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=d3813b2da53bb23bbeff2448fbf38e3b918a821ea3cbb029d3f43b7b7ab07b43

```text
.ce/pr-manifests/ce-p8-review-daemon-s1.md
CHANGELOG.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/review_dry_run.py
validators/creator_engine_validator/forge/review_dry_run_DESIGN.md
validators/tests/unit/test_p8_review_daemon_s1.py
validators/tests/unit/test_version_boundary.py
```
