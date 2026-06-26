---
slug: ce-288-count-agnostic-checks
date: 2026-06-26
kind: pr-manifest
scope: validator tests
issue: ce-ops#288
work_class: story
---

# PR path manifest - ce-ops#288 - count-agnostic registered-check assertions

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-288-count-agnostic-checks` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

- **Declared work class:** story

Scope: ce-ops#288 replaces absolute registered-check total assertions in the
listed unit tests with module-specific membership or non-membership checks.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=a21a40c96820ca244a37f9b02a91a4e8e06c051e93590e376ae21b8ec76dcf3c

```text
.ce/changelog/ce-288-count-agnostic-checks.md
.ce/pr-manifests/ce-288-count-agnostic-checks.md
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
```
