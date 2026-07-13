---
slug: ce-556-arg-indirect-base-exemption
date: 2026-07-13
kind: fixed
scope: validation
issue: ce-ops#556
---

**Resolve ARG-indirected local Docker image bases.**

- Resolve same-file ARG defaults for local image-base exemptions.
- Keep unresolved and external bases on the Buildx validation path.
