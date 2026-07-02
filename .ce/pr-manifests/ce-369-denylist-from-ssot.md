# PR path manifest — ce-369 · Generate the identity denylist from registry source at runtime

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-369-denylist-from-ssot` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=39239db51b50031f895eb300e037f8fc0e0edd36012ef5fa44a4c214d02c03d5

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-369-denylist-from-ssot.md
.ce/pr-manifests/ce-369-denylist-from-ssot.md
.github/workflows/identity-denylist-freshness.yml
.gitignore
scripts/gen_identity_denylist.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/fleet_manifest_guard.py
validators/creator_engine_validator/checks/identity_denylist_autogen_sync.py
validators/creator_engine_validator/identity_denylist.py
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_fleet_manifest_guard.py
validators/tests/unit/test_identity_denylist_autogen_sync.py
```
