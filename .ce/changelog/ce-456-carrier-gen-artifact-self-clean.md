---
slug: ce-456-carrier-gen-artifact-self-clean
date: 2026-07-05
kind: fixed
scope: validator tooling
issue: ce-ops#456
---

**Carrier generator self-cleans stale build artifacts.**

- Exclude stale build/ and *.egg-info artifact paths from generated carrier path manifests.
