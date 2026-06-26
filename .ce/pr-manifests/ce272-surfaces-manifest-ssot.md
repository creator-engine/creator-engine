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

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=47ee41495a1ba21800e6b8f23a4e1e751ca236ff66ebd7c02dd0ca985d1fe14d

```text
.ce/changelog/ce272-surfaces-manifest-ssot.md
.ce/pr-manifests/ce272-surfaces-manifest-ssot.md
surfaces/manifest.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/surfaces_manifest.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_surfaces_manifest.py
validators/tests/unit/test_version_boundary.py
```
