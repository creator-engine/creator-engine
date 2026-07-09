# PR path manifest - ce-502-standby-surface

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-502-standby-surface` and requires
this PR's `base..HEAD` diff to equal exactly the authorized path-set below;
this carrier lists itself.

slug: ce-502-standby-surface

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=719933dbc67aaf1340756d6bbc900e493be5b643740d483ae54c6d706055eb53

```text
.ce/changelog/ce-502-standby-surface.md
.ce/pr-manifests/ce-502-standby-surface.md
deploy/dgx-controller-runsc/provision-standby-surface.sh
tools/mint-forge-token.py
validators/creator_engine_validator/continuity_drill_runtime.py
validators/tests/unit/test_continuity_drill_cli.py
```
