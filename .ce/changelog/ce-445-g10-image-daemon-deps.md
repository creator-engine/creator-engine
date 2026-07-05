---
slug: ce-445-g10-image-daemon-deps
date: 2026-07-05
kind: fixed
scope: deploy
issue: ce-ops#445
---

**Bundle gate-daemon runtime dependencies in canonical images.**

- Install GitHub CLI from the official signed apt repository in both canonical runtime Dockerfiles while preserving offline validator wheel builds.
- Keep `git` installed and add static Dockerfile-content tests for the `gh` keyring/repository pins in `validators/tests/unit/test_runtime_image.py` and `validators/tests/unit/test_oci_image.py`.
