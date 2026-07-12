---
slug: ce-543-image-smoke-tier
date: 2026-07-12
kind: added
scope: validation
issue: ce-ops#543
---

**Add a pinned Dockerfile image-build smoke tier to PR validation.**

- Check committed `deploy/**/Dockerfile` changes with sha-verified hadolint and Docker Buildx `--check` only.
- Keep unchanged carriers as a no-tooling no-op and prohibit image publication flags.
