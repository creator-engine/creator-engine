---
slug: ce273-surfaces-manifest-consistent
date: 2026-06-26
kind: story
scope: [validators/creator_engine_validator/checks/surfaces_manifest.py]
issue: ce-ops#273
---

- **Declared work class:** story

Added the `surfaces_manifest_consistent` validator check to compare manifest
pins against Dockerfiles, shell defaults, and Python requirement pins.
