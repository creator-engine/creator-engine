---
slug: ce-release-0-3-6
date: 2026-07-12
kind: chore
scope: release
issue: 
---

**chore: bump 0.3.5 → 0.3.6 + CHANGELOG + release staging (train 2).**

- Bumps version 0.3.5 → 0.3.6 across pyproject.toml, version.py, _version.py, README, docs, deploy images, test fixtures
- Aggregates 19 changelog fragments landed since release/v0.3.5
- Stages signed release artifacts under .ce/release-staging/0.3.6/ (wheel SHA256: 0905d78218e436605cd18517932250eadc5e042295476d95768459c509b25e88)
- Copies downloads to docs/downloads/0.3.6/
- Updates docs/llms-install.md with placeholder ce-root-v1 signature (content_sha256: 1d3f9a7d65e1a003667b59ff179f3492513c1ccabf2bf6bfa06d5931bb54edaf)
- Updates brain assertions chain for 0.3.6 pyproject.toml
