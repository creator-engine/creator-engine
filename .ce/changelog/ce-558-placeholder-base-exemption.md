---
slug: ce-558-placeholder-base-exemption
date: 2026-07-13
kind: fixed
scope: validation
issue: ce-ops#558
---

**Exempt unresolved placeholder Docker image bases.**

- Classify local and unresolved placeholder FROM references before Buildx.
- Keep hadolint mandatory and external resolved bases on Buildx validation.
