---
slug: ce276-surfaces-check-updates
date: 2026-06-26
kind: feature
scope: [validators/creator_engine_validator/surfaces, validators/tests/unit/test_surfaces_check_updates.py]
issue: ce-ops#276
---

- **Declared work class:** feature

Closes creator-engine/ce-ops#276

This PR adds a read-only `ce surfaces check-updates` command for reporting
current manifest pins against upstream npm, GitHub release, Zig download index,
and PyPI metadata. It does not register a validator check and does not mutate
`surfaces/manifest.yaml`.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=65053fc06c3c0482b34e147a0e8dd3f7c5d5c94fc747a72e7e6e32cb34ebb777

```text
.ce/changelog/ce276-surfaces-check-updates.md
.ce/pr-manifests/ce276-surfaces-check-updates.md
PR_BODY.md
README.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/surfaces/__init__.py
validators/creator_engine_validator/surfaces/check_updates.py
validators/tests/unit/test_surfaces_check_updates.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
