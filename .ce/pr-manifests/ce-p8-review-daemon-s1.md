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

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=bc223c28c033641ac52343b7e2362d65d4e623b26e71d2d2aa32bb717b5830aa

```text
.ce/changelog/ce-p8-review-daemon-s1.md
.ce/pr-manifests/ce-p8-review-daemon-s1.md
CHANGELOG.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/review_dry_run.py
validators/creator_engine_validator/forge/review_dry_run_DESIGN.md
validators/tests/unit/test_p8_review_daemon_s1.py
validators/tests/unit/test_version_boundary.py
```
