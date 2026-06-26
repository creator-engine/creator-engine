---
slug: ce273-surfaces-manifest-consistent
date: 2026-06-26
kind: story
scope: [validators/creator_engine_validator/checks/surfaces_manifest.py]
issue: ce-ops#273
---

- **Declared work class:** story

Closes ce-ops#273

This PR registers `surfaces_manifest_consistent` to enforce consistency between
`surfaces/manifest.yaml` and checked-in surfaces such as Dockerfiles, runsc
launch defaults, and validator Python requirement pins.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=e88284293589413874303fbfd60ce336f050528761aec86d6333f480ef0f45b5

```text
.ce/changelog/ce273-surfaces-manifest-consistent.md
.ce/pr-manifests/ce273-surfaces-manifest-consistent.md
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
