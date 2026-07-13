---
slug: ce-543-local-base-exemption
date: 2026-07-13
kind: changed
scope: validation
issue: ce-ops#543
---

**Exempt local Docker image bases from Buildx smoke checks.**

- Keep hadolint for local `creator-engine/` bases while explicitly exempting their Buildx syntax check.
- Preserve Buildx checks for all nonmatching base images.
