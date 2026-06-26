---
slug: ce272-surfaces-manifest-ssot
date: 2026-06-26
kind: story
scope: [surfaces/manifest.yaml, validators/creator_engine_validator/checks/surfaces_manifest.py]
issue: ce-ops#272
---

- **Declared work class:** story

Closes creator-engine/ce-ops#272

This PR adds `surfaces/manifest.yaml` as the Phase 1 SSOT for rented and
host-only surfaces, then registers `surfaces_manifest_complete` to enforce the
manifest's completeness and currently derivable pins.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=fc7dfa0f1e1755218cb8a08efe017313963a8791764c6618435ba1e24600e969

```text
.ce/changelog/ce272-surfaces-manifest-ssot.md
.ce/pr-manifests/ce272-surfaces-manifest-ssot.md
surfaces/manifest.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_surfaces_manifest.py
```
