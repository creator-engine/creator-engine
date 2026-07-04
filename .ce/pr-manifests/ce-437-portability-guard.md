# PR path manifest — ce-ops#437 · control-plane portability CI guard

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-437-portability-guard` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=6583131b9b2687b5e18223478aaf7af2c9a0b8a1c1a9f92b3d617d6d6d818a8c

```text
.ce/changelog/ce-437-portability-guard.md
.ce/pr-manifests/ce-437-portability-guard.md
surfaces/portability-plane-manifest.yaml
validators/creator_engine_validator/checks/portability_plane.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/pr_preflight.py
validators/tests/unit/test_portability_plane.py
```
