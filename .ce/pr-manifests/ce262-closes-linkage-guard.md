# PR path manifest — ce-ops#262 · add PR closes-linkage guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce262-closes-linkage-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Closes creator-engine/ce-ops#262

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=13

AUTHORIZED_PATHS_SHA256=dd0f86b5a7ba9f17092b4e13c608d92ef00086cfbdf5ff7d5474c3b526433be4

```text
.ce/changelog/ce262-closes-linkage-guard.md
.ce/pr-manifests/ce262-closes-linkage-guard.md
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/pr_closes_linkage.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_pr_closes_linkage.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
```
