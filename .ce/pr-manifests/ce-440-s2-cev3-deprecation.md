# PR path manifest — creator-engine/ce-ops#440 · cev3 deprecation notice and internal-groups lock-in

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-440-s2-cev3-deprecation` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=916a27e070d6803669450f5e6cea1081b40ff8091e2185f77e01abdd365697d6

```text
.ce/changelog/ce-440-s2-cev3-deprecation.md
.ce/pr-manifests/ce-440-s2-cev3-deprecation.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_ce_cli_v3_shim.py
validators/tests/unit/test_integrator_belt.py
```
