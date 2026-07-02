# PR path manifest — ce-369 · Hash identity denylist from registry source

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-369-denylist-from-ssot` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=911f8a987ef63705aa39127d225114d992e2c6addd2f16d06d4f1a3802aec6f2

```text
.ce/changelog/ce-369-denylist-from-ssot.md
.ce/pr-manifests/ce-369-denylist-from-ssot.md
.github/workflows/identity-denylist-freshness.yml
scripts/gen_identity_denylist.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/fleet_manifest_guard.py
validators/creator_engine_validator/checks/identity_denylist_autogen_sync.py
validators/creator_engine_validator/data/identity_denylist.generated.yaml
validators/creator_engine_validator/identity_denylist.py
validators/creator_engine_validator/public_docs_confidentiality.py
validators/pyproject.toml
validators/tests/unit/test_identity_denylist_autogen_sync.py
```
